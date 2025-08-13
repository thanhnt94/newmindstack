# File: Mindstack/web/mindstack_app/modules/admin/content_management/flashcards/routes.py
# Version: 1.0 - Routes và logic cho quản lý Flashcard của admin
# Mục đích: Xử lý các yêu cầu liên quan đến việc tạo, sửa, xóa bộ và thẻ Flashcard (cho admin).

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd # Cần cài đặt: pip install pandas openpyxl

# Import Blueprint từ __init__.py của module này
from . import admin_flashcards_bp 

# Import các model và db instance từ cấp trên (đi lên 4 cấp)
from .....models import LearningContainer, LearningItem, User, SystemSetting
from .....db_instance import db
# Tái sử dụng forms từ my_content/flashcards
from ....my_content.flashcards.forms import FlashcardSetForm, FlashcardItemForm

# Cấu hình thư mục upload (tương tự như my_content/flashcards)
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

# Đảm bảo thư mục upload tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Middleware để đảm bảo người dùng đã đăng nhập và có quyền admin
@admin_flashcards_bp.before_request
@login_required 
def admin_flashcard_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản lý Flashcard của admin.', 'danger')
        abort(403) 

# --- ROUTES QUẢN LÝ BỘ FLASHCARD (LearningContainer) ---
# Admin có thể xem TẤT CẢ các bộ Flashcard, không chỉ của mình
@admin_flashcards_bp.route('/')
@admin_flashcards_bp.route('/sets')
def list_admin_flashcard_sets():
    flashcard_sets = LearningContainer.query.filter_by(
        container_type='FLASHCARD_SET'
    ).all()
    # Lấy thông tin người tạo để hiển thị trong bảng
    users = User.query.all()
    user_map = {user.user_id: user.username for user in users}
    return render_template('admin_flashcard_sets.html', flashcard_sets=flashcard_sets, user_map=user_map)

@admin_flashcards_bp.route('/sets/add', methods=['GET', 'POST'])
def add_admin_flashcard_set():
    form = FlashcardSetForm()
    # Admin có thể gán bộ thẻ cho người dùng khác
    # Thêm trường để chọn creator_user_id vào form nếu muốn admin gán
    # For simplicity, let's assume admin creates for themselves or a default user for now
    # Or we can add a SelectField for creator_user_id if needed.
    
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # Thêm một trường SelectField cho người tạo nếu muốn admin gán cho người khác
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data

        # Admin tạo bộ thẻ, mặc định là admin là người tạo, hoặc có thể chọn từ form
        creator_id = current_user.user_id # Mặc định admin là người tạo
        # if hasattr(form, 'creator') and form.creator.data:
        #     creator_id = int(form.creator.data)

        # Xử lý upload file Excel
        if form.excel_file.data and allowed_file(form.excel_file.data.filename):
            filename = secure_filename(form.excel_file.data.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            form.excel_file.data.save(filepath)

            try:
                df = pd.read_excel(filepath)
                required_cols = ['front', 'back']
                if not all(col in df.columns for col in required_cols):
                    flash('File Excel phải có ít nhất các cột "front" và "back".', 'danger')
                    os.remove(filepath)
                    return render_template('add_edit_admin_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới (Admin)')

                new_set = LearningContainer(
                    creator_user_id=creator_id,
                    container_type='FLASHCARD_SET',
                    title=form.title.data,
                    description=form.description.data,
                    tags=form.tags.data,
                    is_public=form.is_public.data,
                    ai_settings=ai_settings if ai_settings else None
                )
                db.session.add(new_set)
                db.session.flush() 

                for index, row in df.iterrows():
                    item_content = {
                        "front": str(row['front']) if 'front' in row else '',
                        "back": str(row['back']) if 'back' in row else '',
                        "front_audio_content": str(row['front_audio_content']) if 'front_audio_content' in row else None,
                        "front_audio_url": str(row['front_audio_url']) if 'front_audio_url' in row else None,
                        "back_audio_content": str(row['back_audio_content']) if 'back_audio_content' in row else None,
                        "back_audio_url": str(row['back_audio_url']) if 'back_audio_url' in row else None,
                        "front_img": str(row['front_img']) if 'front_img' in row else None,
                        "back_img": str(row['back_img']) if 'back_img' in row else None,
                        "ai_prompt": str(row['ai_prompt']) if 'ai_prompt' in row else None
                    }
                    ai_explanation_data = str(row['ai_explanation']) if 'ai_explanation' in row else None

                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        item_type='FLASHCARD',
                        content=item_content,
                        order_in_container=index,
                        ai_explanation=ai_explanation_data if ai_explanation_data != 'None' else None
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ thẻ Flashcard và các thẻ đã được thêm thành công từ file Excel (Admin)!', 'success')
                os.remove(filepath)
                return redirect(url_for('admin_flashcards.list_admin_flashcard_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel (Admin): {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_admin_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới (Admin)')
        
        else: # Không có file Excel hoặc file không hợp lệ, chỉ tạo bộ thẻ rỗng
            new_set = LearningContainer(
                creator_user_id=creator_id,
                container_type='FLASHCARD_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=form.is_public.data,
                ai_settings=ai_settings if ai_settings else None
            )
            db.session.add(new_set)
            db.session.commit()
            flash('Bộ thẻ Flashcard đã được thêm thành công (Admin)!', 'success')
            return redirect(url_for('admin_flashcards.list_admin_flashcard_sets'))
            
    return render_template('add_edit_admin_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới (Admin)')

@admin_flashcards_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_admin_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    form = FlashcardSetForm(obj=flashcard_set)
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    # Điền dữ liệu AI prompt và creator vào form khi GET request
    if request.method == 'GET':
        if flashcard_set.ai_settings and 'custom_prompt' in flashcard_set.ai_settings:
            form.ai_prompt.data = flashcard_set.ai_settings['custom_prompt']
        # if hasattr(form, 'creator'):
        #     form.creator.data = str(flashcard_set.creator_user_id)

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        flashcard_set.title = form.title.data
        flashcard_set.description = form.description.data
        flashcard_set.tags = form.tags.data
        flashcard_set.is_public = form.is_public.data
        flashcard_set.ai_settings = ai_settings if ai_settings else None
        # if hasattr(form, 'creator'):
        #     flashcard_set.creator_user_id = int(form.creator.data)

        # Xử lý upload file Excel (nếu có file mới, sẽ cập nhật các thẻ hiện có hoặc thêm mới)
        if form.excel_file.data and allowed_file(form.excel_file.data.filename):
            filename = secure_filename(form.excel_file.data.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            form.excel_file.data.save(filepath)

            try:
                df = pd.read_excel(filepath)
                required_cols = ['front', 'back']
                if not all(col in df.columns for col in required_cols):
                    flash('File Excel phải có ít nhất các cột "front" và "back".', 'danger')
                    os.remove(filepath)
                    return render_template('add_edit_admin_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard (Admin)', flashcard_set=flashcard_set)

                # Xóa tất cả các thẻ hiện có trong bộ này trước khi thêm thẻ mới từ Excel
                LearningItem.query.filter_by(container_id=flashcard_set.container_id).delete()
                db.session.flush()

                for index, row in df.iterrows():
                    item_content = {
                        "front": str(row['front']) if 'front' in row else '',
                        "back": str(row['back']) if 'back' in row else '',
                        "front_audio_content": str(row['front_audio_content']) if 'front_audio_content' in row else None,
                        "front_audio_url": str(row['front_audio_url']) if 'front_audio_url' in row else None,
                        "back_audio_content": str(row['back_audio_content']) if 'back_audio_content' in row else None,
                        "back_audio_url": str(row['back_audio_url']) if 'back_audio_url' in row else None,
                        "front_img": str(row['front_img']) if 'front_img' in row else None,
                        "back_img": str(row['back_img']) if 'back_img' in row else None,
                        "ai_prompt": str(row['ai_prompt']) if 'ai_prompt' in row else None
                    }
                    ai_explanation_data = str(row['ai_explanation']) if 'ai_explanation' in row else None

                    new_item = LearningItem(
                        container_id=flashcard_set.container_id,
                        item_type='FLASHCARD',
                        content=item_content,
                        order_in_container=index,
                        ai_explanation=ai_explanation_data if ai_explanation_data != 'None' else None
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ thẻ Flashcard và các thẻ đã được cập nhật từ file Excel (Admin)!', 'success')
                os.remove(filepath)
                return redirect(url_for('admin_flashcards.list_admin_flashcard_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel (Admin): {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_admin_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard (Admin)', flashcard_set=flashcard_set)
        
        else: # Không có file Excel mới, chỉ cập nhật thông tin bộ thẻ
            db.session.commit()
            flash('Thông tin bộ thẻ Flashcard đã được cập nhật (Admin)!', 'success')
            return redirect(url_for('admin_flashcards.list_admin_flashcard_sets'))

    return render_template('add_edit_admin_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard (Admin)', flashcard_set=flashcard_set)

@admin_flashcards_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_admin_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    
    # Admin có quyền xóa bất kỳ bộ thẻ nào
    # if flashcard_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa bộ thẻ này.', 'danger')
    #    abort(403)
    
    # Xóa tất cả các thẻ con trước
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(flashcard_set)
    db.session.commit()
    flash('Bộ thẻ Flashcard đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_flashcards.list_admin_flashcard_sets'))

# --- ROUTES QUẢN LÝ THẺ FLASHCARD (LearningItem) TRONG BỘ ---
# Admin có thể xem TẤT CẢ các thẻ trong bộ, không chỉ của mình
@admin_flashcards_bp.route('/sets/<int:set_id>/items')
def list_admin_flashcard_items(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền xem bộ thẻ này
    # if flashcard_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xem bộ thẻ này.', 'danger')
    #    abort(403)
    
    flashcard_items = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='FLASHCARD'
    ).order_by(LearningItem.order_in_container).all() 

    return render_template('admin_flashcard_items.html', flashcard_set=flashcard_set, flashcard_items=flashcard_items)

@admin_flashcards_bp.route('/sets/<int:set_id>/items/add', methods=['GET', 'POST'])
def add_admin_flashcard_item(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền thêm thẻ vào bộ thẻ này
    # if flashcard_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền thêm thẻ vào bộ thẻ này.', 'danger')
    #    abort(403)

    form = FlashcardItemForm()
    if form.validate_on_submit():
        item_content = {
            "front": form.front.data,
            "back": form.back.data,
            "front_audio_content": form.front_audio_content.data if form.front_audio_content.data else None,
            "front_audio_url": form.front_audio_url.data if form.front_audio_url.data else None,
            "back_audio_content": form.back_audio_content.data if form.back_audio_content.data else None,
            "back_audio_url": form.back_audio_url.data if form.back_audio_url.data else None,
            "front_img": form.front_img.data if form.front_img.data else None,
            "back_img": form.back_img.data if form.back_img.data else None,
            # ai_prompt cấp thẻ có thể được thêm vào đây nếu có trường trong form
            # "ai_prompt": form.ai_prompt.data if form.ai_prompt.data else None
        }
        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content=item_content,
            order_in_container=LearningItem.query.filter_by(container_id=set_id).count() 
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Thẻ Flashcard đã được thêm thành công (Admin)!', 'success')
        return redirect(url_for('admin_flashcards.list_admin_flashcard_items', set_id=set_id))
    
    return render_template('add_edit_admin_flashcard_item.html', form=form, title='Thêm Thẻ Flashcard mới (Admin)', flashcard_set=flashcard_set)

@admin_flashcards_bp.route('/sets/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_admin_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.get_or_404(item_id)

    # Đảm bảo thẻ thuộc bộ thẻ
    if flashcard_item.container_id != set_id:
        flash('Thẻ không thuộc bộ thẻ này.', 'danger')
        abort(403)
    # Admin có quyền chỉnh sửa thẻ này
    # if flashcard_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền chỉnh sửa thẻ này.', 'danger')
    #    abort(403)

    form = FlashcardItemForm(obj=flashcard_item)
    
    # Điền dữ liệu từ JSON content vào form khi GET request
    if request.method == 'GET':
        if flashcard_item.content:
            form.front.data = flashcard_item.content.get('front', '')
            form.back.data = flashcard_item.content.get('back', '')
            form.front_audio_content.data = flashcard_item.content.get('front_audio_content', '')
            form.front_audio_url.data = flashcard_item.content.get('front_audio_url', '')
            form.back_audio_content.data = flashcard_item.content.get('back_audio_content', '')
            form.back_audio_url.data = flashcard_item.content.get('back_audio_url', '')
            form.front_img.data = flashcard_item.content.get('front_img', '')
            form.back_img.data = flashcard_item.content.get('back_img', '')
            form.ai_explanation.data = flashcard_item.ai_explanation # Điền dữ liệu giải thích AI

    if form.validate_on_submit():
        # Cập nhật dữ liệu vào JSON content
        flashcard_item.content['front'] = form.front.data
        flashcard_item.content['back'] = form.back.data
        flashcard_item.content['front_audio_content'] = form.front_audio_content.data if form.front_audio_content.data else None
        flashcard_item.content['front_audio_url'] = form.front_audio_url.data if form.front_audio_url.data else None
        flashcard_item.content['back_audio_content'] = form.back_audio_content.data if form.back_audio_content.data else None
        flashcard_item.content['back_audio_url'] = form.back_audio_url.data if form.back_audio_url.data else None
        flashcard_item.content['front_img'] = form.front_img.data if form.front_img.data else None
        flashcard_item.content['back_img'] = form.back_img.data if form.back_img.data else None
        # ai_prompt cấp thẻ có thể được cập nhật vào đây nếu có trường trong form
        # flashcard_item.content['ai_prompt'] = form.ai_prompt.data if form.ai_prompt.data else None
        
        # ai_explanation không được sửa trực tiếp qua form này
        # flashcard_item.ai_explanation = form.ai_explanation.data # KHÔNG NÊN LÀM VẬY NẾU CHỈ ĐỂ HIỂN THỊ

        db.session.commit()
        flash('Thẻ Flashcard đã được cập nhật thành công (Admin)!', 'success')
        return redirect(url_for('admin_flashcards.list_admin_flashcard_items', set_id=set_id))

    return render_template('add_edit_admin_flashcard_item.html', form=form, title='Sửa Thẻ Flashcard (Admin)', flashcard_set=flashcard_set, flashcard_item=flashcard_item)

@admin_flashcards_bp.route('/sets/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
def delete_admin_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.get_or_404(item_id)

    if flashcard_item.container_id != set_id:
        flash('Thẻ không thuộc bộ thẻ này.', 'danger')
        abort(403)
    # Admin có quyền xóa thẻ này
    # if flashcard_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa thẻ này.', 'danger')
    #    abort(403)
    
    db.session.delete(flashcard_item)
    db.session.commit()
    flash('Thẻ Flashcard đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_flashcards.list_admin_flashcard_items', set_id=set_id))

# File: Mindstack/web/mindstack_app/modules/my_content/flashcards/routes.py
# Version: 1.0 - Routes và logic cho quản lý Flashcard của người dùng
# Mục đích: Xử lý các yêu cầu liên quan đến việc tạo, sửa, xóa bộ và thẻ Flashcard.

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd # Cần cài đặt: pip install pandas openpyxl

# Import Blueprint từ __init__.py của module này
from . import flashcards_bp 

# Import các model và db instance từ cấp trên
from ....models import LearningContainer, LearningItem, User, SystemSetting
from ....db_instance import db
from .forms import FlashcardSetForm, FlashcardItemForm

# Cấu hình thư mục upload (cần được định nghĩa trong config.py hoặc ở đây)
# Tạm thời định nghĩa ở đây, sau này có thể chuyển vào config.py
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

# Đảm bảo thư mục upload tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Middleware để đảm bảo người dùng đã đăng nhập cho toàn bộ Blueprint flashcards
@flashcards_bp.before_request
@login_required 
def flashcard_management_required():
    # Chỉ cần người dùng đã đăng nhập
    pass

# --- ROUTES QUẢN LÝ BỘ FLASHCARD (LearningContainer) ---

@flashcards_bp.route('/')
@flashcards_bp.route('/sets')
def list_flashcard_sets():
    # Lấy tất cả các bộ Flashcard do người dùng hiện tại tạo
    flashcard_sets = LearningContainer.query.filter_by(
        creator_user_id=current_user.user_id,
        container_type='FLASHCARD_SET'
    ).all()
    return render_template('flashcard_sets.html', flashcard_sets=flashcard_sets)

@flashcards_bp.route('/sets/add', methods=['GET', 'POST'])
def add_flashcard_set():
    form = FlashcardSetForm()
    if form.validate_on_submit():
        # Xử lý AI settings
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data

        # Xử lý upload file Excel
        if form.excel_file.data and allowed_file(form.excel_file.data.filename):
            filename = secure_filename(form.excel_file.data.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            form.excel_file.data.save(filepath)

            try:
                df = pd.read_excel(filepath)
                # Kiểm tra các cột bắt buộc
                required_cols = ['front', 'back']
                if not all(col in df.columns for col in required_cols):
                    flash('File Excel phải có ít nhất các cột "front" và "back".', 'danger')
                    os.remove(filepath) # Xóa file lỗi
                    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới')

                # Tạo LearningContainer
                new_set = LearningContainer(
                    creator_user_id=current_user.user_id,
                    container_type='FLASHCARD_SET',
                    title=form.title.data,
                    description=form.description.data,
                    tags=form.tags.data,
                    is_public=form.is_public.data,
                    ai_settings=ai_settings if ai_settings else None
                )
                db.session.add(new_set)
                db.session.flush() # Lấy ID của new_set trước khi commit

                # Thêm các LearningItem từ Excel
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
                        # ai_prompt cấp thẻ có thể được thêm vào đây nếu có cột trong Excel
                        "ai_prompt": str(row['ai_prompt']) if 'ai_prompt' in row else None
                    }
                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        item_type='FLASHCARD',
                        content=item_content,
                        order_in_container=index # Giữ thứ tự từ Excel
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ thẻ Flashcard và các thẻ đã được thêm thành công từ file Excel!', 'success')
                os.remove(filepath) # Xóa file sau khi xử lý
                return redirect(url_for('flashcards.list_flashcard_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel: {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới')
        
        else: # Không có file Excel hoặc file không hợp lệ, chỉ tạo bộ thẻ rỗng
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='FLASHCARD_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=form.is_public.data,
                ai_settings=ai_settings if ai_settings else None
            )
            db.session.add(new_set)
            db.session.commit()
            flash('Bộ thẻ Flashcard đã được thêm thành công!', 'success')
            return redirect(url_for('flashcards.list_flashcard_sets'))
            
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ Thẻ Flashcard mới')

@flashcards_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    # Đảm bảo người dùng hiện tại là người tạo bộ thẻ này
    if flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền chỉnh sửa bộ thẻ này.', 'danger')
        abort(403)

    form = FlashcardSetForm(obj=flashcard_set)
    
    # Điền dữ liệu AI prompt vào form khi GET request
    if request.method == 'GET' and flashcard_set.ai_settings and 'custom_prompt' in flashcard_set.ai_settings:
        form.ai_prompt.data = flashcard_set.ai_settings['custom_prompt']

    if form.validate_on_submit():
        # Xử lý AI settings
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        flashcard_set.title = form.title.data
        flashcard_set.description = form.description.data
        flashcard_set.tags = form.tags.data
        flashcard_set.is_public = form.is_public.data
        flashcard_set.ai_settings = ai_settings if ai_settings else None

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
                    return render_template('add_edit_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard', flashcard_set=flashcard_set)

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
                    new_item = LearningItem(
                        container_id=flashcard_set.container_id,
                        item_type='FLASHCARD',
                        content=item_content,
                        order_in_container=index
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ thẻ Flashcard và các thẻ đã được cập nhật từ file Excel!', 'success')
                os.remove(filepath)
                return redirect(url_for('flashcards.list_flashcard_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel: {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard', flashcard_set=flashcard_set)
        
        else: # Không có file Excel mới, chỉ cập nhật thông tin bộ thẻ
            db.session.commit()
            flash('Thông tin bộ thẻ Flashcard đã được cập nhật!', 'success')
            return redirect(url_for('flashcards.list_flashcard_sets'))

    return render_template('add_edit_flashcard_set.html', form=form, title='Sửa Bộ Thẻ Flashcard', flashcard_set=flashcard_set)

@flashcards_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền xóa bộ thẻ này.', 'danger')
        abort(403)
    
    # Xóa tất cả các thẻ con trước
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(flashcard_set)
    db.session.commit()
    flash('Bộ thẻ Flashcard đã được xóa thành công!', 'success')
    return redirect(url_for('flashcards.list_flashcard_sets'))

# --- ROUTES QUẢN LÝ THẺ FLASHCARD (LearningItem) TRONG BỘ ---

@flashcards_bp.route('/sets/<int:set_id>/items')
def list_flashcard_items(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền xem bộ thẻ này.', 'danger')
        abort(403)
    
    # Lấy các thẻ Flashcard thuộc bộ này
    flashcard_items = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='FLASHCARD'
    ).order_by(LearningItem.order_in_container).all() # Sắp xếp theo thứ tự

    return render_template('flashcard_items.html', flashcard_set=flashcard_set, flashcard_items=flashcard_items)

@flashcards_bp.route('/sets/<int:set_id>/items/add', methods=['GET', 'POST'])
def add_flashcard_item(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền thêm thẻ vào bộ thẻ này.', 'danger')
        abort(403)

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
            # order_in_container có thể được tính toán tự động (ví dụ: max + 1)
            order_in_container=LearningItem.query.filter_by(container_id=set_id).count() 
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Thẻ Flashcard đã được thêm thành công!', 'success')
        return redirect(url_for('flashcards.list_flashcard_items', set_id=set_id))
    
    return render_template('add_edit_flashcard_item.html', form=form, title='Thêm Thẻ Flashcard mới', flashcard_set=flashcard_set)

@flashcards_bp.route('/sets/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.get_or_404(item_id)

    # Đảm bảo thẻ thuộc bộ thẻ và người dùng là người tạo
    if flashcard_item.container_id != set_id or flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền chỉnh sửa thẻ này.', 'danger')
        abort(403)

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
        
        # ai_explanation không được sửa trực tiếp qua form này, nhưng có thể được AI tạo ra
        # flashcard_item.ai_explanation = form.ai_explanation.data # KHÔNG NÊN LÀM VẬY NẾU CHỈ ĐỂ HIỂN THỊ

        db.session.commit()
        flash('Thẻ Flashcard đã được cập nhật thành công!', 'success')
        return redirect(url_for('flashcards.list_flashcard_items', set_id=set_id))

    return render_template('add_edit_flashcard_item.html', form=form, title='Sửa Thẻ Flashcard', flashcard_set=flashcard_set, flashcard_item=flashcard_item)

@flashcards_bp.route('/sets/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
def delete_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.get_or_404(item_id)

    if flashcard_item.container_id != set_id or flashcard_set.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền xóa thẻ này.', 'danger')
        abort(403)
    
    db.session.delete(flashcard_item)
    db.session.commit()
    flash('Thẻ Flashcard đã được xóa thành công!', 'success')
    return redirect(url_for('flashcards.list_flashcard_items', set_id=set_id))

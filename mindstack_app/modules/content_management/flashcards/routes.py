# File: newmindstack/mindstack_app/modules/content_management/flashcards/routes.py
# Phiên bản: 3.9 (Đã tích hợp tiện ích phân trang và tìm kiếm từ utils)
# Mục đích: Xử lý các route liên quan đến quản lý bộ thẻ ghi nhớ (LearningContainer loại 'FLASHCARD_SET')
#           Bao gồm tạo, xem, chỉnh sửa, xóa bộ thẻ và các thẻ ghi nhớ (LearningItem loại 'FLASHCARD')
#           Áp dụng logic phân quyền để kiểm tra người dùng có quyền truy cập/chỉnh sửa hay không.
#           Bổ sung logic để phục vụ nội dung riêng cho yêu cầu AJAX từ dashboard tổng quan.
#           Đã sửa lỗi BuildError bằng cách cập nhật tên endpoint trong url_for.
#           ĐÃ SỬA: Chuyển hướng sau khi thêm/sửa/xóa về content_dashboard và chọn tab đúng.
#           ĐÃ SỬA: Điều chỉnh để trả về JSON cho các yêu cầu AJAX khi thêm/sửa/xóa bộ.
#           ĐÃ SỬA: Render template bare form cho yêu cầu GET từ modal, full form cho non-modal GET.
#           ĐÃ CẢI TIẾN: Logic xử lý upload file Excel, đọc các cột đầy đủ và tạo FlashcardItem từ đó.
#           ĐÃ SỬA: Đếm số lượng thẻ chính xác và truyền vào template.
#           ĐÃ SỬA: Route edit_flashcard_item hỗ trợ mở trong modal.
#           ĐÃ TÍCH HỢP: Phân trang và tìm kiếm sử dụng các hàm từ utils.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from ..forms import FlashcardSetForm, FlashcardItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....utils.pagination import get_pagination_data # THÊM: Import hàm phân trang
from ....utils.search import apply_search_filter # THÊM: Import hàm tìm kiếm

# Định nghĩa Blueprint cho quản lý thẻ ghi nhớ
flashcards_bp = Blueprint('content_management_flashcards', __name__,
                            template_folder='../templates/flashcards')

@flashcards_bp.route('/flashcards')
@login_required
def list_flashcard_sets():
    """
    Hiển thị danh sách các bộ thẻ ghi nhớ mà người dùng hiện tại có quyền truy cập,
    có hỗ trợ phân trang và tìm kiếm.
    Admin có thể thấy tất cả các bộ thẻ.
    Người dùng thông thường chỉ thấy bộ thẻ do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách bộ thẻ.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)

    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')

    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_sets_query = base_query.filter_by(creator_user_id=user_id)
        contributed_sets_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_sets_query.union(contributed_sets_query)

    # Áp dụng tìm kiếm
    search_fields = [LearningContainer.title, LearningContainer.description, LearningContainer.tags]
    base_query = apply_search_filter(base_query, search_query, search_fields)

    # Phân trang
    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    flashcard_sets = pagination.items

    # Đếm số lượng item cho mỗi bộ thẻ
    for set_item in flashcard_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='FLASHCARD'
        ).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_flashcard_sets_list.html', flashcard_sets=flashcard_sets, pagination=pagination, search_query=search_query)
    else:
        return render_template('flashcard_sets.html', flashcard_sets=flashcard_sets, pagination=pagination, search_query=search_query)

@flashcards_bp.route('/flashcards/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_set():
    """
    Thêm một bộ thẻ ghi nhớ mới.
    Chỉ người dùng đã đăng nhập mới có thể thêm bộ thẻ.
    Người tạo bộ thẻ sẽ tự động là creator_user_id.
    """
    form = FlashcardSetForm()
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None

        try:
            # Tạo bộ thẻ mới
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='FLASHCARD_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=form.is_public.data,
                ai_settings={'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
            )
            db.session.add(new_set)
            db.session.flush() # Lấy new_set.container_id trước khi commit

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name

                df = pd.read_excel(temp_filepath)
                
                # Định nghĩa các cột cần thiết và tùy chọn
                required_cols = ['front', 'back']
                optional_cols = ['front_audio_content', 'back_audio_content', 'front_img', 'back_img']

                # Kiểm tra các cột bắt buộc
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel phải có các cột bắt buộc: {', '.join(required_cols)}.")

                # Thêm các thẻ ghi nhớ từ file Excel
                for index, row in df.iterrows():
                    front_content = str(row['front']) if pd.notna(row['front']) else ''
                    back_content = str(row['back']) if pd.notna(row['back']) else ''

                    if front_content and back_content:
                        item_content = {
                            'front': front_content,
                            'back': back_content
                        }
                        # Thêm các cột tùy chọn nếu chúng tồn tại và có giá trị
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])

                        new_item = LearningItem(
                            container_id=new_set.container_id,
                            item_type='FLASHCARD',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                
                flash_message = 'Bộ thẻ ghi nhớ và các thẻ từ Excel đã được tạo thành công!'
                flash_category = 'success'

            else: # Không có file Excel được tải lên
                flash_message = 'Bộ thẻ ghi nhớ mới đã được tạo thành công!'
                flash_category = 'success'
            
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý file Excel hoặc tạo bộ thẻ: {str(e)}'
            flash_category = 'danger'
            # Nếu là AJAX, trả về lỗi
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': flash_message}), 400
            else:
                flash(flash_message, flash_category)
                return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
            
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        # Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    # Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Thêm Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_set(set_id):
    """
    Chỉnh sửa thông tin bộ thẻ ghi nhớ.
    Chỉ creator_user_id hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bộ thẻ này.'}), 403
        else:
            abort(403)

    form = FlashcardSetForm(obj=flashcard_set)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None

        try:
            flashcard_set.title = form.title.data
            flashcard_set.description = form.description.data
            flashcard_set.tags = form.tags.data
            flashcard_set.is_public = form.is_public.data
            flashcard_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None

            # Xử lý file Excel nếu có (khi chỉnh sửa, sẽ xóa cũ và thêm mới các item)
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name

                df = pd.read_excel(temp_filepath)
                
                required_cols = ['front', 'back']
                optional_cols = ['front_audio_content', 'back_audio_content', 'front_img', 'back_img']

                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel phải có các cột bắt buộc: {', '.join(required_cols)}.")

                # Xóa tất cả các thẻ ghi nhớ cũ của bộ này trước khi thêm mới từ Excel
                LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD').delete()
                db.session.flush()

                for index, row in df.iterrows():
                    front_content = str(row['front']) if pd.notna(row['front']) else ''
                    back_content = str(row['back']) if pd.notna(row['back']) else ''

                    if front_content and back_content:
                        item_content = {
                            'front': front_content,
                            'back': back_content
                        }
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])

                        new_item = LearningItem(
                            container_id=set_id,
                            item_type='FLASHCARD',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                
                flash_message = 'Bộ thẻ ghi nhớ và các thẻ từ Excel đã được cập nhật thành công!'
                flash_category = 'success'

            else: # Không có file Excel được tải lên, chỉ cập nhật thông tin bộ thẻ
                flash_message = 'Bộ thẻ ghi nhớ đã được cập nhật thành công!'
                flash_category = 'success'

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý file Excel hoặc cập nhật bộ thẻ: {str(e)}'
            flash_category = 'danger'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': flash_message}), 400
            else:
                flash(flash_message, flash_category)
                return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_flashcard_set(set_id):
    """
    Xóa một bộ thẻ ghi nhớ.
    Chỉ creator_user_id hoặc admin mới có thể xóa bộ thẻ.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and flashcard_set.creator_user_id != current_user.user_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bộ thẻ này.'}), 403
        else:
            flash('Bạn không có quyền xóa bộ thẻ này.', 'danger')
            abort(403)

    db.session.delete(flashcard_set)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bộ thẻ ghi nhớ đã được xóa thành công!'})
    else:
        flash('Bộ thẻ ghi nhớ đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='flashcards'))

@flashcards_bp.route('/flashcards/<int:set_id>/items')
@login_required
def list_flashcard_items(set_id):
    """
    Hiển thị danh sách các thẻ ghi nhớ thuộc một bộ thẻ cụ thể.
    Người dùng cần có quyền xem bộ thẻ đó.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if not flashcard_set.is_public and \
       current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403)

    # THÊM: Lấy các tham số phân trang và tìm kiếm cho item
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)

    base_query = LearningItem.query.filter_by(
        container_id=flashcard_set.container_id,
        item_type='FLASHCARD'
    )

    # THÊM: Áp dụng tìm kiếm cho item
    search_fields = [LearningItem.content['front'], LearningItem.content['back']] # Tìm kiếm trong JSON content
    base_query = apply_search_filter(base_query, search_query, search_fields)

    # THÊM: Phân trang cho item
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    flashcard_items = pagination.items

    can_edit = False
    if current_user.user_role == 'admin' or \
       flashcard_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        can_edit = True

    return render_template('flashcard_items.html', flashcard_set=flashcard_set, flashcard_items=flashcard_items, can_edit=can_edit, pagination=pagination, search_query=search_query)

@flashcards_bp.route('/flashcards/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_item(set_id):
    """
    Thêm thẻ ghi nhớ mới vào một bộ thẻ.
    Chỉ người tạo bộ thẻ hoặc người dùng được cấp quyền 'editor' mới có thể thêm.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền thêm thẻ ghi nhớ vào bộ này.'}), 403
        else:
            abort(403)

    form = FlashcardItemForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='FLASHCARD'
        ).scalar()
        new_order = (max_order or 0) + 1

        # Cập nhật để lưu trữ tất cả các trường vào content
        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content={
                'front': form.front.data,
                'back': form.back.data,
                'front_audio_content': form.front_audio_content.data if form.front_audio_content.data else None,
                'front_audio_url': form.front_audio_url.data if form.front_audio_url.data else None,
                'back_audio_content': form.back_audio_content.data if form.back_audio_content.data else None,
                'back_audio_url': form.back_audio_url.data if form.back_audio_url.data else None,
                'front_img': form.front_img.data if form.front_img.data else None,
                'back_img': form.back_img.data if form.back_img.data else None,
            },
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thẻ ghi nhớ mới đã được thêm thành công!'})
        else:
            flash('Thẻ ghi nhớ mới đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', form=form, flashcard_set=flashcard_set, title='Thêm Thẻ ghi nhớ')
    return render_template('add_edit_flashcard_item.html', form=form, flashcard_set=flashcard_set, title='Thêm Thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_item(set_id, item_id):
    """
    Chỉnh sửa một thẻ ghi nhớ cụ thể trong bộ thẻ.
    Chỉ người tạo bộ thẻ hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()

    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa thẻ ghi nhớ này.'}), 403
        else:
            abort(403)

    # Khởi tạo form với dữ liệu hiện có từ trường 'content' dạng JSON
    form = FlashcardItemForm(
        front=flashcard_item.content.get('front', ''),
        back=flashcard_item.content.get('back', ''),
        front_audio_content=flashcard_item.content.get('front_audio_content', ''),
        front_audio_url=flashcard_item.content.get('front_audio_url', ''),
        back_audio_content=flashcard_item.content.get('back_audio_content', ''),
        back_audio_url=flashcard_item.content.get('back_audio_url', ''),
        front_img=flashcard_item.content.get('front_img', ''),
        back_img=flashcard_item.content.get('back_img', '')
    )
    
    if form.validate_on_submit():
        flashcard_item.content = {
            'front': form.front.data,
            'back': form.back.data,
            'front_audio_content': form.front_audio_content.data if form.front_audio_content.data else None,
            'front_audio_url': form.front_audio_url.data if form.front_audio_url.data else None,
            'back_audio_content': form.back_audio_content.data if form.back_audio_content.data else None,
            'back_audio_url': form.back_audio_url.data if form.back_audio_url.data else None,
            'front_img': form.front_img.data if form.front_img.data else None,
            'back_img': form.back_img.data if form.back_img.data else None,
        }
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thẻ ghi nhớ đã được cập nhật thành công!'})
        else:
            flash('Thẻ ghi nhớ đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', form=form, flashcard_set=flashcard_set, flashcard_item=flashcard_item, title='Chỉnh sửa Thẻ ghi nhớ')
    return render_template('add_edit_flashcard_item.html', form=form, flashcard_set=flashcard_set, flashcard_item=flashcard_item, title='Chỉnh sửa Thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    """
    Xóa một thẻ ghi nhớ cụ thể trong bộ thẻ.
    Chỉ người tạo bộ thẻ hoặc người dùng được cấp quyền 'editor' mới có thể xóa.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()

    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa thẻ ghi nhớ này.'}), 403
        else:
            abort(403)

    db.session.delete(flashcard_item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Thẻ ghi nhớ đã được xóa thành công!'})
    else:
        flash('Thẻ ghi nhớ đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='flashcards'))

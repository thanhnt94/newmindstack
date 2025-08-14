# File: newmindstack/mindstack_app/modules/content_management/flashcards/routes.py
# Phiên bản: 3.0
# Mục đích: Xử lý các route liên quan đến quản lý bộ thẻ ghi nhớ (LearningContainer loại 'FLASHCARD_SET')
#           Bao gồm tạo, xem, chỉnh sửa, xóa bộ thẻ và các thẻ ghi nhớ (LearningItem loại 'FLASHCARD')
#           Áp dụng logic phân quyền để kiểm tra người dùng có quyền truy cập/chỉnh sửa hay không.
#           Bổ sung logic để phục vụ nội dung riêng cho yêu cầu AJAX từ dashboard tổng quan.
#           Đã sửa lỗi BuildError bằng cách cập nhật tên endpoint trong url_for.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from ..forms import FlashcardSetForm, FlashcardItemForm # Import form từ thư mục cha (content_management)
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User # Đã sửa đường dẫn import models

# Định nghĩa Blueprint cho quản lý thẻ ghi nhớ
flashcards_bp = Blueprint('content_management_flashcards', __name__,
                          template_folder='../templates/flashcards')

@flashcards_bp.route('/flashcards')
@login_required
def list_flashcard_sets():
    """
    Hiển thị danh sách các bộ thẻ ghi nhớ mà người dùng hiện tại có quyền truy cập.
    Admin có thể thấy tất cả các bộ thẻ.
    Người dùng thông thường chỉ thấy bộ thẻ do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách bộ thẻ.
    """
    flashcard_sets = []
    if current_user.user_role == 'admin':
        # Admin thấy tất cả các bộ thẻ
        flashcard_sets = LearningContainer.query.filter_by(container_type='FLASHCARD_SET').all()
    else:
        # Người dùng thường thấy bộ thẻ của mình tạo hoặc được cấp quyền
        user_id = current_user.user_id
        
        # Lấy các container_id mà người dùng hiện tại là người tạo
        created_sets_query = LearningContainer.query.filter_by(
            creator_user_id=user_id,
            container_type='FLASHCARD_SET'
        )

        # Lấy các container_id mà người dùng hiện tại được cấp quyền chỉnh sửa
        contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
            LearningContainer.container_type == 'FLASHCARD_SET'
        )
        
        # Kết hợp hai truy vấn để lấy danh sách các bộ thẻ duy nhất
        flashcard_sets = created_sets_query.union(contributed_sets_query).all()

    # Kiểm tra nếu đây là yêu cầu AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Nếu là AJAX, chỉ render phần danh sách các bộ thẻ
        return render_template('_flashcard_sets_list.html', flashcard_sets=flashcard_sets)
    else:
        # Nếu không phải AJAX, render toàn bộ trang như bình thường
        return render_template('flashcard_sets.html', flashcard_sets=flashcard_sets)

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
        new_set = LearningContainer(
            creator_user_id=current_user.user_id,
            container_type='FLASHCARD_SET',
            title=form.title.data,
            description=form.description.data,
            tags=form.tags.data,
            is_public=form.is_public.data
        )
        db.session.add(new_set)
        db.session.commit()
        flash('Bộ thẻ ghi nhớ mới đã được tạo thành công!', 'success')
        # DÒNG ĐƯỢC CHỈNH SỬA
        return redirect(url_for('content_management.content_management_flashcards.list_flashcard_sets'))
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_set(set_id):
    """
    Chỉnh sửa thông tin bộ thẻ ghi nhớ.
    Chỉ creator_user_id hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403) # Forbidden nếu không có quyền

    form = FlashcardSetForm(obj=flashcard_set) # Điền dữ liệu hiện có vào form
    if form.validate_on_submit():
        flashcard_set.title = form.title.data
        flashcard_set.description = form.description.data
        flashcard_set.tags = form.tags.data
        flashcard_set.is_public = form.is_public.data
        db.session.commit()
        flash('Bộ thẻ ghi nhớ đã được cập nhật thành công!', 'success')
        # DÒNG ĐƯỢC CHỈNH SỬA
        return redirect(url_for('content_management.content_management_flashcards.list_flashcard_sets'))
    return render_template('add_edit_flashcard_set.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_flashcard_set(set_id):
    """
    Xóa một bộ thẻ ghi nhớ.
    Chỉ creator_user_id hoặc admin mới có thể xóa bộ thẻ.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền xóa
    if current_user.user_role != 'admin' and flashcard_set.creator_user_id != current_user.user_id:
        abort(403) # Forbidden nếu không có quyền

    db.session.delete(flashcard_set)
    db.session.commit()
    flash('Bộ thẻ ghi nhớ đã được xóa thành công!', 'success')
    # DÒNG ĐƯỢC CHỈNH SỬA
    return redirect(url_for('content_management.content_management_flashcards.list_flashcard_sets'))

@flashcards_bp.route('/flashcards/<int:set_id>/items')
@login_required
def list_flashcard_items(set_id):
    """
    Hiển thị danh sách các thẻ ghi nhớ thuộc một bộ thẻ cụ thể.
    Người dùng cần có quyền xem bộ thẻ đó.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền xem bộ thẻ: public, là người tạo, hoặc là contributor
    if not flashcard_set.is_public and \
       current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403) # Forbidden nếu không có quyền

    flashcard_items = LearningItem.query.filter_by(
        container_id=flashcard_set.container_id,
        item_type='FLASHCARD'
    ).order_by(LearningItem.order_in_container).all()

    # Xác định quyền chỉnh sửa để truyền xuống template
    can_edit = False
    if current_user.user_role == 'admin' or \
       flashcard_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        can_edit = True

    return render_template('flashcard_items.html', flashcard_set=flashcard_set, flashcard_items=flashcard_items, can_edit=can_edit)

@flashcards_bp.route('/flashcards/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_item(set_id):
    """
    Thêm thẻ ghi nhớ mới vào một bộ thẻ.
    Chỉ người tạo bộ thẻ hoặc người dùng được cấp quyền 'editor' mới có thể thêm.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403) # Forbidden nếu không có quyền

    form = FlashcardItemForm()
    if form.validate_on_submit():
        # Tìm số thứ tự lớn nhất hiện có và tăng lên 1
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='FLASHCARD'
        ).scalar()
        new_order = (max_order or 0) + 1

        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content={'front': form.front_content.data, 'back': form.back_content.data}, # Lưu nội dung dưới dạng JSON
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Thẻ ghi nhớ mới đã được thêm thành công!', 'success')
        # DÒNG ĐƯỢC CHỈNH SỬA
        return redirect(url_for('content_management.content_management_flashcards.list_flashcard_items', set_id=set_id))
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

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403) # Forbidden nếu không có quyền

    # Khởi tạo form với dữ liệu hiện có từ trường 'content' dạng JSON
    form = FlashcardItemForm(front_content=flashcard_item.content.get('front'), back_content=flashcard_item.content.get('back'))
    
    if form.validate_on_submit():
        flashcard_item.content = {'front': form.front_content.data, 'back': form.back_content.data}
        db.session.commit()
        flash('Thẻ ghi nhớ đã được cập nhật thành công!', 'success')
        # DÒNG ĐƯỢC CHỈNH SỬA
        return redirect(url_for('content_management.content_management_flashcards.list_flashcard_items', set_id=set_id))
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

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403) # Forbidden nếu không có quyền

    db.session.delete(flashcard_item)
    db.session.commit()
    flash('Thẻ ghi nhớ đã được xóa thành công!', 'success')
    # DÒNG ĐƯỢC CHỈNH SỬA
    return redirect(url_for('content_management.content_management_flashcards.list_flashcard_items', set_id=set_id))


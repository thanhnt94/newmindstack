# File: newmindstack/mindstack_app/modules/content_management/routes.py
# Phiên bản: 2.0
# Mục đích: Định nghĩa các route cấp cao cho module quản lý nội dung chung.
#           Đây là nơi người dùng sẽ truy cập để xem dashboard tổng quan về nội dung của họ,
#           và có thể quản lý người đóng góp cho các LearningContainer.
#           Đã sửa lỗi ImportError: attempted relative import beyond top-level package.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from ...models import db, LearningContainer, ContainerContributor, User # DÒNG ĐƯỢC CHỈNH SỬA: Đã giảm số dấu chấm
from .forms import FlashcardSetForm # Chỉ ví dụ, bạn có thể cần thêm các form khác tùy chức năng

# Import các blueprint con
from .courses.routes import courses_bp
from .flashcards.routes import flashcards_bp
from .quizzes.routes import quizzes_bp

# Định nghĩa Blueprint chính cho content_management
content_management_bp = Blueprint('content_management', __name__,
                                  template_folder='templates')

# Đăng ký các blueprint con
content_management_bp.register_blueprint(courses_bp, url_prefix='/courses')
content_management_bp.register_blueprint(flashcards_bp, url_prefix='/flashcards')
content_management_bp.register_blueprint(quizzes_bp, url_prefix='/quizzes')

@content_management_bp.route('/')
@login_required
def content_dashboard():
    """
    Hiển thị dashboard tổng quan về nội dung.
    Đây sẽ là nơi người dùng thấy các link đến quản lý Khóa học, Thẻ ghi nhớ, Bộ câu hỏi.
    Admin sẽ có một số tùy chọn quản lý người dùng hoặc hệ thống ở đây.
    """
    return render_template('content_dashboard.html')

@content_management_bp.route('/manage_contributors/<int:container_id>', methods=['GET', 'POST'])
@login_required
def manage_contributors(container_id):
    """
    Quản lý người đóng góp cho một LearningContainer cụ thể.
    Chỉ người tạo (creator_user_id) hoặc admin mới có quyền truy cập trang này.
    """
    container = LearningContainer.query.get_or_404(container_id)

    # Kiểm tra quyền quản lý người đóng góp: chỉ creator hoặc admin
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        abort(403) # Forbidden nếu không có quyền

    # Xử lý thêm người đóng góp mới
    if request.method == 'POST':
        user_id_to_add = request.form.get('user_id_to_add')
        permission_level = request.form.get('permission_level', 'editor') # Mặc định là editor

        if user_id_to_add:
            try:
                user_id_to_add = int(user_id_to_add)
                user_to_add = User.query.get(user_id_to_add)

                if not user_to_add:
                    flash(f'Không tìm thấy người dùng với ID: {user_id_to_add}.', 'danger')
                elif user_to_add.user_id == container.creator_user_id:
                    flash('Không thể thêm người tạo làm người đóng góp.', 'warning')
                else:
                    # Kiểm tra xem người dùng đã là contributor chưa
                    existing_contributor = ContainerContributor.query.filter_by(
                        container_id=container_id,
                        user_id=user_id_to_add
                    ).first()

                    if existing_contributor:
                        # Cập nhật quyền nếu đã tồn tại
                        existing_contributor.permission_level = permission_level
                        flash(f'Cấp độ quyền của {user_to_add.username} đã được cập nhật.', 'info')
                    else:
                        # Thêm người đóng góp mới
                        new_contributor = ContainerContributor(
                            container_id=container_id,
                            user_id=user_id_to_add,
                            permission_level=permission_level
                        )
                        db.session.add(new_contributor)
                        flash(f'{user_to_add.username} đã được thêm làm người đóng góp!', 'success')
                    db.session.commit()
            except ValueError:
                flash('ID người dùng không hợp lệ.', 'danger')
        else:
            flash('Vui lòng nhập ID người dùng.', 'danger')
        
        # Xử lý xóa người đóng góp
        if 'remove_contributor_id' in request.form:
            remove_id = request.form.get('remove_contributor_id')
            try:
                remove_id = int(remove_id)
                contributor_to_remove = ContainerContributor.query.filter_by(
                    container_id=container_id,
                    user_id=remove_id
                ).first()
                if contributor_to_remove:
                    db.session.delete(contributor_to_remove)
                    db.session.commit()
                    flash(f'Người đóng góp với ID {remove_id} đã bị xóa.', 'success')
                else:
                    flash('Không tìm thấy người đóng góp này.', 'danger')
            except ValueError:
                flash('ID người đóng góp không hợp lệ.', 'danger')

        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    # Lấy danh sách những người đóng góp hiện có
    contributors = db.session.query(ContainerContributor, User).join(User).filter(
        ContainerContributor.container_id == container_id
    ).all()
    
    return render_template('manage_contributors.html', container=container, contributors=contributors)


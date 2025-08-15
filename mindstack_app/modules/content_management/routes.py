# File: newmindstack/mindstack_app/modules/content_management/routes.py
# Phiên bản: 2.2
# ĐÃ SỬA: Khắc phục lỗi 404 bằng cách loại bỏ url_prefix khi đăng ký các blueprint con.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from ...models import db, LearningContainer, ContainerContributor, User
from .forms import ContributorForm # SỬA: Import form mới

# Import các blueprint con
from .courses.routes import courses_bp
from .flashcards.routes import flashcards_bp
from .quizzes.routes import quizzes_bp

# Định nghĩa Blueprint chính cho content_management
content_management_bp = Blueprint('content_management', __name__,
                                  template_folder='templates') # Vẫn giữ template_folder này cho các template chung

# Đăng ký các blueprint con
# ĐÃ SỬA: Loại bỏ url_prefix vì các routes con đã tự định nghĩa đường dẫn đầy đủ
content_management_bp.register_blueprint(courses_bp)
content_management_bp.register_blueprint(flashcards_bp)
content_management_bp.register_blueprint(quizzes_bp)

@content_management_bp.route('/')
@login_required
def content_dashboard():
    """
    Hiển thị dashboard tổng quan về nội dung.
    """
    return render_template('content_dashboard.html')

@content_management_bp.route('/manage_contributors/<int:container_id>', methods=['GET', 'POST'])
@login_required
def manage_contributors(container_id):
    """
    Quản lý người đóng góp cho một LearningContainer cụ thể.
    """
    container = LearningContainer.query.get_or_404(container_id)

    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        abort(403)

    form = ContributorForm()

    if form.validate_on_submit():
        email_to_add = form.email.data
        permission_level = form.permission_level.data
        
        user_to_add = User.query.filter_by(email=email_to_add).first() # Giả định model User có trường email

        if not user_to_add:
            flash(f'Không tìm thấy người dùng với email: {email_to_add}.', 'danger')
        elif user_to_add.user_id == container.creator_user_id:
            flash('Không thể thêm chính người tạo làm người đóng góp.', 'warning')
        else:
            existing_contributor = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=user_to_add.user_id
            ).first()

            if existing_contributor:
                existing_contributor.permission_level = permission_level
                db.session.commit()
                flash(f'Cấp độ quyền của {user_to_add.username} đã được cập nhật.', 'info')
            else:
                new_contributor = ContainerContributor(
                    container_id=container_id,
                    user_id=user_to_add.user_id,
                    permission_level=permission_level
                )
                db.session.add(new_contributor)
                db.session.commit()
                flash(f'{user_to_add.username} đã được thêm làm người đóng góp!', 'success')
        
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    # Xử lý xóa người đóng góp (giữ nguyên logic cũ)
    if request.method == 'POST' and 'remove_contributor_id' in request.form:
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
                flash(f'Người đóng góp đã bị xóa.', 'success')
            else:
                flash('Không tìm thấy người đóng góp này.', 'danger')
        except ValueError:
            flash('ID người đóng góp không hợp lệ.', 'danger')
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    contributors = db.session.query(ContainerContributor, User).join(User).filter(
        ContainerContributor.container_id == container_id
    ).all()
    
    return render_template('manage_contributors.html', container=container, contributors=contributors, form=form)


from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from .. import blueprint
from ..services.user_service import UserService
from mindstack_app.modules.auth.models import User
from mindstack_app.modules.auth.forms import UserForm
from mindstack_app.core.extensions import db

def admin_required():
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        abort(403)

@blueprint.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('modules/user_management/profile.html', user=current_user)

@blueprint.route('/')
@blueprint.route('/list')
@login_required
def manage_users():
    """Admin: Manage users list."""
    admin_required()
    page = request.args.get('page', 1, type=int)
    pagination = UserService.get_all_users(page=page)
    return render_template('admin/modules/admin/users/users.html', users=pagination.items, pagination=pagination)

@blueprint.route('/add', methods=['GET', 'POST'])
@login_required
def add_user():
    """Admin: Add a new user."""
    admin_required()
    form = UserForm()
    if form.validate_on_submit():
        user_data = {
            'username': form.username.data,
            'email': form.email.data,
            'user_role': form.user_role.data,
            'password': form.password.data
        }
        user = UserService.create_user(user_data)
        if user:
            flash('Người dùng đã được thêm thành công!', 'success')
            return redirect(url_for('user_management.manage_users'))
        flash('Lỗi khi thêm người dùng.', 'danger')
        
    return render_template('admin/modules/admin/users/add_edit_user.html', form=form, title='Thêm Người Dùng Mới')

@blueprint.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Admin: Edit existing user."""
    admin_required()
    user = UserService.get_user_by_id(user_id)
    if not user:
        abort(404)
        
    form = UserForm(obj=user)
    form.user = user
    
    if form.validate_on_submit():
        data = {
            'email': form.email.data,
            'user_role': form.user_role.data
        }
        if form.password.data:
            data['password'] = form.password.data
            
        if UserService.update_user_profile(user_id, data):
            flash('Thông tin người dùng đã được cập nhật!', 'success')
            return redirect(url_for('user_management.manage_users'))
        flash('Lỗi khi cập nhật.', 'danger')

    return render_template('admin/modules/admin/users/add_edit_user.html', form=form, title='Sửa Người Dùng', user=user)

@blueprint.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Admin: Delete user."""
    admin_required()
    if user_id == current_user.user_id:
        flash('Bạn không thể tự xóa tài khoản của mình.', 'danger')
    else:
        if UserService.delete_user(user_id):
            flash('Người dùng đã được xóa thành công!', 'success')
        else:
            flash('Lỗi khi xóa người dùng.', 'danger')
            
    return redirect(url_for('user_management.manage_users'))

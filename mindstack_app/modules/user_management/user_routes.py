# File: Mindstack/web/mindstack_app/modules/admin/user_management/user_routes.py
# Version: 1.1 - Đã thêm logic xử lý trường email vào các route add_user và edit_user.
# Mục đích: Chứa các route và logic cho việc quản lý người dùng trong khu vực admin.

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

# Import Blueprint từ module cha
from . import blueprint
from mindstack_app.models import User # Import model User từ cấp trên (đi lên 3 cấp)
from mindstack_app.core.extensions import db
from mindstack_app.modules.auth.forms import UserForm 

# Middleware để kiểm tra quyền admin cho toàn bộ Blueprint user_management
@blueprint.before_request 
@login_required 
def admin_required():
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        flash('Bạn không có quyền truy cập trang quản trị người dùng.', 'danger')
        abort(403)

# Route để hiển thị danh sách người dùng
@blueprint.route('/') # Đường dẫn gốc của Blueprint user_management
@blueprint.route('/list')
def manage_users():
    users = User.query.all() 
    return render_template('admin/users/users.html', users=users)

# Route để thêm người dùng mới
@blueprint.route('/add', methods=['GET', 'POST'])
def add_user():
    form = UserForm()
    form.user = None # Đảm bảo validate_username hiểu đây là thêm mới
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append('Vui lòng nhập mật khẩu.')
            return render_template('admin/users/add_edit_user.html', form=form, title='Thêm Người Dùng Mới')
        if form.password.data != form.password2.data:
            form.password2.errors.append('Mật khẩu không khớp.')
            return render_template('admin/users/add_edit_user.html', form=form, title='Thêm Người Dùng Mới')

        # THAY ĐỔI: Thêm trường email khi khởi tạo đối tượng User
        user = User(username=form.username.data, email=form.email.data, user_role=form.user_role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Người dùng đã được thêm thành công!', 'success')
        return redirect(url_for('user_management.manage_users'))
    return render_template('admin/users/add_edit_user.html', form=form, title='Thêm Người Dùng Mới')

# Route để sửa thông tin người dùng
@blueprint.route('/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user) 
    form.user = user # Gán user object vào form để validate_username sử dụng user_id để loại trừ
    
    if form.validate_on_submit():
        user.username = form.username.data
        # THAY ĐỔI: Cập nhật trường email
        user.email = form.email.data
        user.user_role = form.user_role.data
        
        if form.password.data:
            if form.password.data != form.password2.data:
                form.password2.errors.append('Mật khẩu không khớp.')
                return render_template('admin/users/add_edit_user.html', form=form, title='Sửa Người Dùng', user=user)
            user.set_password(form.password.data)
        
        db.session.commit()
        flash('Thông tin người dùng đã được cập nhật!', 'success')
        return redirect(url_for('user_management.manage_users'))
    
    elif request.method == 'GET':
        form.user_role.data = user.user_role 

    return render_template('admin/users/add_edit_user.html', form=form, title='Sửa Người Dùng', user=user)

# Route để xóa người dùng
@blueprint.route('/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.user_id == current_user.user_id:
        flash('Bạn không thể tự xóa tài khoản của mình.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Người dùng đã được xóa thành công!', 'success')
    return redirect(url_for('user_management.manage_users'))

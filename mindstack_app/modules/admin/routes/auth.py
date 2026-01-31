# File: mindstack_app/modules/admin/routes/auth.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user
from mindstack_app.models import User
from .. import blueprint
from ..forms import AdminLoginForm

@blueprint.before_request 
def admin_required():
    """
    Mô tả: Middleware (bộ lọc) chạy trước mọi request vào blueprint.
    Đảm bảo chỉ người dùng có vai trò 'admin' mới được truy cập.
    """
    if request.endpoint == 'admin.login':
        return

    if not current_user.is_authenticated:
        return redirect(url_for('admin.login', next=request.url))

    if current_user.is_authenticated and current_user.user_role != User.ROLE_ADMIN:
        flash('Vui lòng đăng nhập với tài khoản Admin.', 'warning')
        return redirect(url_for('admin.login', next=request.url))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """Separate login route for Administrators."""
    if current_user.is_authenticated:
        if current_user.user_role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        
        from flask_login import logout_user
        logout_user()
        flash('Đã đăng xuất tài khoản thường. Vui lòng đăng nhập Admin.', 'info')
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Admin ID hoặc Security Key không đúng.', 'danger')
            return redirect(url_for('admin.login'))
        
        if user.user_role != 'admin':
            flash('Truy cập bị từ chối: Tài khoản này không có quyền Quản trị.', 'danger')
            return redirect(url_for('admin.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            from mindstack_app.modules.gamification.services.scoring_service import ScoreService
            ScoreService.record_daily_login(user.user_id)
        except Exception:
            pass

        flash('Chào mừng Quản trị viên! Đã truy cập hệ thống an toàn.', 'success')
        next_page = request.args.get('next')
        if not next_page or url_for(next_page.lstrip('/')) == url_for('landing.index'):
            next_page = url_for('admin.admin_dashboard')
        return redirect(next_page)
        
    return render_template('admin/login.html', form=form)

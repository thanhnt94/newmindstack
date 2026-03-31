from flask import render_template, flash, redirect, url_for, request, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, timezone
from mindstack_app.core.extensions import db
from .. import auth_bp as blueprint
from ..models import User, UserSession
from ..forms import LoginForm, RegistrationForm
from ..services.auth_service import AuthService

@blueprint.before_app_request
def update_last_seen():
    """Update user's last_seen timestamp."""
    if current_user.is_authenticated:
        now = datetime.now(timezone.utc)
        last_seen = current_user.last_seen
        if last_seen and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
            
        if last_seen is None or (now - last_seen).total_seconds() > 300:
            current_user.last_seen = now
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

@blueprint.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """STRICT LOCAL LOGIN: Always bypasses SSO for emergency admin access."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User.query.filter_by(email=form.username.data).first()
            
        if user and user.check_password(form.password.data) and user.user_role == User.ROLE_ADMIN:
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('dashboard.dashboard'))
        
        flash('Sai thông tin hoặc bạn không có quyền Admin.', 'danger')

    # Clear session to prevent any stale SSO state on GET
    from flask import session
    session.clear()
    return render_dynamic_template('modules/auth/login/login.html', form=form, is_admin_login=True)

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if AuthService.get_config('AUTH_LOGIN_DISABLED', False):
        flash('Chức năng đăng nhập hiện đang tạm khóa.', 'info')
        return redirect(url_for('landing.index'))

    # Simple SSO handoff: Only if central is enabled
    auth_provider = AuthService.get_config('AUTH_PROVIDER', 'local')
    if request.method == 'GET' and auth_provider == 'central' and request.endpoint == 'auth.login':
        return redirect(url_for('auth_center.login'))

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = AuthService.authenticate_user(form.username.data, form.password.data)
        if user:
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('dashboard.dashboard'))
        flash('Sai thông tin đăng nhập.', 'danger')
        
    return render_dynamic_template('modules/auth/login/login.html', form=form, current_auth_mode=auth_provider)

@blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    auth_provider = AuthService.get_config('AUTH_PROVIDER', 'local')
    if auth_provider == 'central':
        return redirect(url_for('auth_center.logout'))
        
    logout_user()
    return redirect(url_for('landing.index'))

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    auth_provider = AuthService.get_config('AUTH_PROVIDER', 'local')
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            AuthService.register_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            flash('Chúc mừng, bạn đã đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi đăng ký: {str(e)}', 'danger')
        
    return render_dynamic_template('modules/auth/register/register.html', form=form, current_auth_mode=auth_provider)

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

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if AuthService.get_config('AUTH_LOGIN_DISABLED', False):
        flash('Chức năng đăng nhập hiện đang tạm khóa.', 'info')
        return redirect(url_for('landing.index'))

    # Bridge: Redirect to SSO if provider is set to central
    auth_provider = AuthService.get_config('AUTH_PROVIDER', 'local')
    if auth_provider == 'central' and request.endpoint == 'auth.login':
        return redirect(url_for('auth_center.login', **request.args))

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    auth_provider = AuthService.get_config('AUTH_PROVIDER', 'local')
    form = LoginForm()
    
    if form.validate_on_submit():
        user = AuthService.authenticate_user(form.username.data, form.password.data)
        if user is None:
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            from mindstack_app.core.signals import user_logged_in
            user_logged_in.send(current_app._get_current_object(), user=current_user)
        except Exception:
            pass

        flash('Đăng nhập thành công!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard.dashboard')
        return redirect(next_page)
        
    return render_dynamic_template('modules/auth/login/login.html', form=form, current_auth_mode=auth_provider)

@blueprint.route('/emergency-login', methods=['GET', 'POST'])
def emergency_login():
    """Fallback Authentication Route for Admins."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
        
    form = LoginForm()
    if request.method == 'GET':
        flash('EMERGENCY MODE: Authenticated via Local Database Bypass', 'warning')
        
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User.query.filter_by(email=form.username.data).first()
            
        if user and user.check_password(form.password.data):
            if user.user_role == User.ROLE_ADMIN:
                login_user(user, remember=form.remember_me.data)
                flash('Emergency Admin Access Granted.', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Cần quyền Quản trị viên cho tuyến đường khẩn cấp này.', 'danger')
        else:
            flash('Thông tin xác thực không chính xác trong CSDL dự phòng.', 'danger')
            
        return redirect(url_for('auth.emergency_login'))
        
    current_auth_mode = AuthService.get_config('AUTH_PROVIDER', 'local')
    return render_dynamic_template('modules/auth/login/login.html', form=form, emergency=True, current_auth_mode=current_auth_mode)

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

# Tệp: web/mindstack_app/modules/auth/routes.py
# Version: 1.0
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user
from . import auth_bp
from .forms import LoginForm, RegistrationForm
from ...models import User, UserSession
from datetime import datetime, timezone
from ...db_instance import db

@auth_bp.before_app_request
def update_last_seen():
    """Update user's last_seen timestamp."""
    if current_user.is_authenticated:
        # Use timezone-aware UTC
        now = datetime.now(timezone.utc)
        
        last_seen = current_user.last_seen
        # If DB returns naive datetime, assume UTC
        if last_seen and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
            
        # Update only if 5 minutes have passed since last update
        if last_seen is None or \
           (now - last_seen).total_seconds() > 300:
            current_user.last_seen = now
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            from ...modules.gamification.services.scoring_service import ScoreService
            ScoreService.record_daily_login(user.user_id)
        except Exception as e:
            # Login should verify succeed even if gamification fails
            pass

        flash('Đăng nhập thành công!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or url_for(next_page.lstrip('/')) == url_for('landing.index'):
            next_page = url_for('dashboard.dashboard')
        return redirect(next_page)
        
    return render_template('v3/pages/auth/login/login.html', form=form)

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('landing.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            user_role=User.ROLE_FREE,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush() # Flush to get user_id

        # Create default session state
        user_session = UserSession(user_id=user.user_id)
        db.session.add(user_session)

        db.session.commit()
        flash('Chúc mừng, bạn đã đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('v3/pages/auth/register/register.html', form=form)

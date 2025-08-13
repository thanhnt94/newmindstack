# Tệp: web/mindstack_app/modules/main/routes.py
# Version: 1.0
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import main_bp

@main_bp.route('/')
def index():
    # Nếu đã đăng nhập, vào dashboard, nếu chưa thì vào trang login
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required # Yêu cầu người dùng phải đăng nhập để truy cập route này
def dashboard():
    # Tạm thời chỉ hiển thị một trang chào mừng
    return render_template('main/dashboard.html')

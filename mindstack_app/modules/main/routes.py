# Tệp: web/mindstack_app/modules/main/routes.py
# Version: 1.1
# Mục đích: Định nghĩa Blueprint và import các routes liên quan.
# ĐÃ SỬA: Thay đổi logic route '/' để hiển thị trang giới thiệu thay vì redirect thẳng đến trang login.

from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import main_bp

@main_bp.route('/')
def index():
    """
    Mô tả: Trang chủ của ứng dụng.
    Nếu người dùng đã đăng nhập, chuyển hướng đến dashboard.
    Nếu chưa, hiển thị trang giới thiệu.
    """
    if current_user.is_authenticated:
        # Nếu đã đăng nhập, vào dashboard
        return redirect(url_for('main.dashboard'))
    # Nếu chưa đăng nhập, hiển thị trang giới thiệu
    return render_template('main/landing_page.html')

@main_bp.route('/dashboard')
@login_required # Yêu cầu người dùng phải đăng nhập để truy cập route này
def dashboard():
    # Tạm thời chỉ hiển thị một trang chào mừng
    return render_template('main/dashboard.html')
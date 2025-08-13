# File: Mindstack/web/mindstack_app/modules/admin/routes.py
# Version: 2.0 - Đã refactor logic quản lý người dùng sang module con
# Mục đích: Chứa các route và logic cho bảng điều khiển admin tổng quan.

from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from . import admin_bp # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.

# Middleware để kiểm tra quyền admin cho toàn bộ Blueprint admin
@admin_bp.before_request 
@login_required 
def admin_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản trị.', 'danger')
        abort(403) 

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def admin_dashboard():
    # Trang dashboard của admin, có thể thêm số liệu thống kê hoặc liên kết đến các module con
    return render_template('dashboard.html')

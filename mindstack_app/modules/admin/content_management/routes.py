# File: Mindstack/web/mindstack_app/modules/admin/content_management/routes.py
# Version: 1.0
# Mục đích: Chứa các route và logic cho trang dashboard quản lý nội dung của admin.

from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

# Import Blueprint từ __init__.py của module này
from . import admin_content_bp 

# Import các model và db instance từ cấp trên (đi lên 3 cấp)
from ....models import LearningContainer, LearningItem, User

# Middleware để đảm bảo người dùng đã đăng nhập và có quyền admin cho toàn bộ Blueprint admin_content
@admin_content_bp.before_request
@login_required 
def admin_content_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản lý nội dung của admin.', 'danger')
        abort(403) 

# Route cho trang dashboard quản lý nội dung của admin
@admin_content_bp.route('/')
@admin_content_bp.route('/dashboard')
def admin_content_dashboard():
    # Trang dashboard này sẽ hiển thị các liên kết đến quản lý Flashcard, Quiz, Course (cho admin)
    return render_template('admin_content_dashboard.html')

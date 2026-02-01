# File: mindstack_app/modules/admin/__init__.py
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import current_user
from .context_processors import admin_context_processor

admin_bp = Blueprint('admin', __name__)
admin_bp.app_context_processor(admin_context_processor)

@admin_bp.before_request 
def admin_required():
    """
    Mô tả: Middleware (bộ lọc) chạy trước mọi request vào blueprint.
    Đảm bảo chỉ người dùng có vai trò 'admin' mới được truy cập.
    """
    from mindstack_app.models import User
    
    if request.endpoint == 'admin.login':
        return

    if not current_user.is_authenticated:
        return redirect(url_for('admin.login', next=request.url))

    if current_user.is_authenticated and current_user.user_role != User.ROLE_ADMIN:
        flash('Vui lòng đăng nhập với tài khoản Admin.', 'warning')
        return redirect(url_for('admin.login', next=request.url))

module_metadata = {
    'name': 'Quản trị hệ thống',
    'icon': 'cogs',
    'category': 'System',
    'url_prefix': '/admin',
    'admin_route': 'admin.admin_dashboard',
    'enabled': True
}

def setup_module(app):
    from . import routes

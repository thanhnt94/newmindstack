# File: mindstack_app/modules/user_management/__init__.py
from flask import Blueprint

# Tên Blueprint PHẢI là 'user_management' để khớp với url_for('user_management.manage_users')
blueprint = Blueprint('user_management', __name__)

module_metadata = {
    'name': 'Quản lý người dùng',
    'icon': 'users',
    'category': 'System',
    'url_prefix': '/admin/users',
    'admin_route': 'user_management.manage_users',
    'enabled': True
}

def setup_module(app):
    # Đăng ký các routes vào blueprint này
    from . import routes
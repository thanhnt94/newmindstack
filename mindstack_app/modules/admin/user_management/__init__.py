# File: Mindstack/web/mindstack_app/modules/admin/user_management/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con quản lý người dùng
user_management_bp = Blueprint('user_management', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import user_routes

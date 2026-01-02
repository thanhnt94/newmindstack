# File: Mindstack/web/mindstack_app/modules/admin/user_management/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý người dùng.

from flask import Blueprint

from ..context_processors import admin_context_processor

# Tạo đối tượng Blueprint cho module con quản lý người dùng
user_management_bp = Blueprint('user_management', __name__)

# Sử dụng chung context processor để có dữ liệu sidebar/thanh điều hướng đồng nhất
user_management_bp.app_context_processor(admin_context_processor)

# Import các routes để chúng được đăng ký với Blueprint
from . import user_routes

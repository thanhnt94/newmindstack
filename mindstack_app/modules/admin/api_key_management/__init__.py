# File: mindstack_app/modules/admin/api_key_management/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module quản lý API key.

from flask import Blueprint

from ..context_processors import admin_context_processor

# Tạo đối tượng Blueprint
api_key_management_bp = Blueprint(
    'api_key_management',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Dùng chung context processor để giao diện admin luôn đầy đủ dữ liệu
api_key_management_bp.app_context_processor(admin_context_processor)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes
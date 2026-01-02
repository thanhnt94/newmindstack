# File: Mindstack/web/mindstack_app/modules/admin/content_management/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint chính cho module quản lý nội dung của admin.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module content_management
admin_content_management_bp = Blueprint('content_management', __name__)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

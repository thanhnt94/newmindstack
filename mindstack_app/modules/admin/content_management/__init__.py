# File: Mindstack/web/mindstack_app/modules/admin/content_management/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint chính cho module quản lý nội dung của admin.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module admin_content
admin_content_bp = Blueprint('admin_content', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

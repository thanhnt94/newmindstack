# File: Mindstack/web/mindstack_app/modules/admin/__init__.py
# Version: 1.2 - Đã đổi tên thư mục template để khắc phục TemplateNotFound
# Mục đích: Định nghĩa Blueprint cho module admin và quản lý import routes.

from flask import Blueprint

# 1. Tạo đối tượng Blueprint cho module admin
# Chỉ định tên thư mục template mới
admin_bp = Blueprint('admin', __name__, template_folder='admin_templates')

# 2. Import các routes ở cuối để chúng được đăng ký với Blueprint.
# Điều này đảm bảo admin_bp đã được định nghĩa trước khi routes.py sử dụng nó.
from . import routes

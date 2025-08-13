# File: Mindstack/web/mindstack_app/modules/my_content/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint chính cho module quản lý nội dung của người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module my_content
my_content_bp = Blueprint('my_content', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

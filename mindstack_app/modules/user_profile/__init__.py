# File: Mindstack/web/mindstack_app/modules/user_profile/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module quản lý profile người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module user_profile
user_profile_bp = Blueprint('user_profile', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

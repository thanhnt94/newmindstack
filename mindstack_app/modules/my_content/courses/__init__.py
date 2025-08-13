# File: Mindstack/web/mindstack_app/modules/my_content/courses/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý Khóa học của người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con courses
courses_bp = Blueprint('courses', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

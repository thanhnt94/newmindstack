# File: Mindstack/web/mindstack_app/modules/admin/content_management/courses/__init__.py
# Version: 1.3 - Giải pháp cuối cùng cho lỗi circular import
# Mục đích: Định nghĩa Blueprint cho module con quản lý Khóa học của admin.

# Import Blueprint từ file routes.py nơi nó được định nghĩa
from .routes import admin_courses_bp 

# Không cần định nghĩa Blueprint ở đây nữa, chỉ cần import nó từ routes.py
# from flask import Blueprint
# admin_courses_bp = Blueprint('admin_courses', __name__, template_folder='templates')

# Không cần import routes ở đây nữa vì admin_courses_bp đã được import từ routes
# from . import routes

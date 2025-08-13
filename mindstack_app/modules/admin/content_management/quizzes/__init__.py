# File: Mindstack/web/mindstack_app/modules/admin/content_management/quizzes/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý Quiz của admin.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con admin_quizzes
admin_quizzes_bp = Blueprint('admin_quizzes', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

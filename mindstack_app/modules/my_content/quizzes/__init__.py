# File: Mindstack/web/mindstack_app/modules/my_content/quizzes/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý Quiz của người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con quizzes
quizzes_bp = Blueprint('quizzes', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

# File: Mindstack/web/mindstack_app/modules/admin/content_management/flashcards/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho module con quản lý Flashcard của admin.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con admin_flashcards
admin_flashcards_bp = Blueprint('admin_flashcards', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

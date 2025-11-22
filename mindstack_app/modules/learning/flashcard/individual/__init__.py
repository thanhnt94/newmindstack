# File: mindstack_app/modules/learning/flashcard/individual/__init__.py
# Mục đích: Định nghĩa Blueprint cho module học Flashcard cá nhân.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module học Flashcard cá nhân
flashcard_learning_bp = Blueprint(
    'flashcard_learning', __name__, template_folder='templates'
)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes  # noqa: E402,F401
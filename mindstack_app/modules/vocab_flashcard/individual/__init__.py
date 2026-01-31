# File: mindstack_app/modules/learning/flashcard/individual/__init__.py
# Mục đích: Định nghĩa Blueprint cho module học Flashcard cá nhân.

from flask import Blueprint
import os

# Current file: mindstack_app/modules/learning/flashcard/individual/__init__.py
# Target: mindstack_app/modules/learning/flashcard/individual/templates
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')

# Tạo đối tượng Blueprint cho module học Flashcard cá nhân
flashcard_learning_bp = Blueprint(
    'flashcard_learning',
    __name__
)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes  # noqa: E402,F401

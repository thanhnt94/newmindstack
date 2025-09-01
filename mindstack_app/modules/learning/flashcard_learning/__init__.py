# File: mindstack_app/modules/learning/flashcard_learning/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module học Flashcard.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con học Flashcard
flashcard_learning_bp = Blueprint('flashcard_learning', __name__,
                                  template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes
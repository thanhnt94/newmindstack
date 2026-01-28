# File: mindstack_app/modules/AI/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module dịch vụ AI.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module AI
ai_bp = Blueprint('AI', __name__)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes
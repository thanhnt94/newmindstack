# Tệp: web/mindstack_app/modules/main/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint và import các routes liên quan.

from flask import Blueprint

# 1. Tạo đối tượng Blueprint
main_bp = Blueprint('main', __name__, template_folder='templates')

# 2. Import các routes ở cuối để chúng được đăng ký với Blueprint
from . import routes

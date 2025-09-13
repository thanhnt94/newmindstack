# File: mindstack_app/modules/ai_services/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module dịch vụ AI.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module ai_services
ai_services_bp = Blueprint('ai_services', __name__, template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes
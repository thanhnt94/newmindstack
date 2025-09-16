# File: mindstack_app/modules/stats/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module thống kê.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module stats
stats_bp = Blueprint(
    'stats', 
    __name__, 
    template_folder='templates'
)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

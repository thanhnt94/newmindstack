# File: mindstack_app/modules/notes/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module ghi chú của người dùng.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module notes
notes_bp = Blueprint('notes', __name__)

# Import các routes để chúng được đăng ký với Blueprint
from . import routes
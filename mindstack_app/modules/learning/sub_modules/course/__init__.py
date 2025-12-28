# mindstack_app/modules/learning/course/__init__.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint cho module học Course.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module con học Course
course_bp = Blueprint('course', __name__,
                                  template_folder='templates')

# Import các routes để chúng được đăng ký với Blueprint
from . import routes

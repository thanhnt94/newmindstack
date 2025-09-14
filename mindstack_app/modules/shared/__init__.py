# File: mindstack_app/modules/shared/__init__.py
# Version: 1.0
# Mục đích: Định nghĩa Blueprint cho các thành phần dùng chung (templates, utils).
#           Blueprint này không có routes, chỉ dùng để Flask nhận diện thư mục template.

from flask import Blueprint

# Tạo đối tượng Blueprint cho module shared
# template_folder='templates' để Flask biết nơi tìm base.html và các includes
shared_bp = Blueprint('shared', __name__, template_folder='templates')

# Module này không cần import routes vì nó không có trang web nào để hiển thị
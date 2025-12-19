# File: mindstack_app/modules/learning/memrise/__init__.py
# Mục đích: Khởi tạo module Memrise

from flask import Blueprint

memrise_bp = Blueprint(
    'memrise', __name__, url_prefix='/memrise', template_folder='templates'
)

from . import routes  # noqa: E402, F401

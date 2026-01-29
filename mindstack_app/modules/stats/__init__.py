"""
Stats Module
Thống kê và phân tích dữ liệu học tập.
"""
from flask import Blueprint

stats_bp = Blueprint(
    'stats',
    __name__,
    static_folder='static',
    url_prefix='/stats'
)

from .routes import *  # noqa: E402, F401
from .services.analytics_listener import init_analytics_listener

# Initialize listeners
init_analytics_listener()


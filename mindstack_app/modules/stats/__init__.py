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


"""
Gamification Module
Quản lý hệ thống điểm số, huy hiệu và thành tích.
"""
from flask import Blueprint

gamification_bp = Blueprint(
    'gamification', 
    __name__, 
    url_prefix='/admin/gamification'
)

from . import routes  # noqa: E402, F401

# File: mindstack_app/modules/stats/__init__.py
from flask import Blueprint

blueprint = Blueprint('stats', __name__)

module_metadata = {
    'name': 'Thống kê',
    'icon': 'chart-bar',
    'category': 'System',
    'url_prefix': '/stats',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from .services.analytics_listener import init_analytics_listener
    init_analytics_listener()

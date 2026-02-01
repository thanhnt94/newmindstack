from flask import Blueprint

blueprint = Blueprint('scoring', __name__, url_prefix='/admin/scoring')

module_metadata = {
    'name': 'Quản lý Điểm số',
    'icon': 'trophy',
    'category': 'System',
    'url_prefix': '/admin/scoring',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from .events import init_events
    init_events(app)

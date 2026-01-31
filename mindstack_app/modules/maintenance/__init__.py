from flask import Blueprint

blueprint = Blueprint('maintenance', __name__, url_prefix='/admin/maintenance')

module_metadata = {
    'name': 'Chế độ Bảo trì',
    'icon': 'wrench',
    'category': 'System',
    'url_prefix': '/admin/maintenance',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from .middleware import register_maintenance_middleware
    register_maintenance_middleware(app)

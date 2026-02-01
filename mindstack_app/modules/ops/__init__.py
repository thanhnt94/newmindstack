from flask import Blueprint

blueprint = Blueprint('ops', __name__, url_prefix='/admin/ops')

module_metadata = {
    'name': 'System Operations',
    'icon': 'biohazard',
    'category': 'System',
    'url_prefix': '/admin/ops',
    'enabled': True
}

def setup_module(app):
    from . import routes

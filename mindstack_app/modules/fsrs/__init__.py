from flask import Blueprint

blueprint = Blueprint('fsrs', __name__, url_prefix='/admin/fsrs')

module_metadata = {
    'name': 'FSRS Algorithm',
    'icon': 'brain',
    'category': 'System',
    'url_prefix': '/admin/fsrs',
    'enabled': True
}

def setup_module(app):
    from . import routes

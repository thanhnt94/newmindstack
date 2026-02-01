from flask import Blueprint

blueprint = Blueprint('backup', __name__, url_prefix='/admin/backup')

module_metadata = {
    'name': 'Backup & Restore',
    'icon': 'database',
    'category': 'System',
    'url_prefix': '/admin/backup',
    'enabled': True
}

def setup_module(app):
    from . import routes

# File: mindstack_app/modules/translator/__init__.py
from flask import Blueprint

blueprint = Blueprint('translator', __name__, static_folder='static')

module_metadata = {
    'name': 'Dịch thuật',
    'icon': 'languages',
    'category': 'System',
    'url_prefix': '/translator',
    'enabled': True
}

def setup_module(app):
    from . import routes

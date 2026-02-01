# File: mindstack_app/modules/notes/__init__.py
from flask import Blueprint

blueprint = Blueprint('notes', __name__)

module_metadata = {
    'name': 'Ghi chú',
    'icon': 'edit',
    'category': 'Learning',
    'url_prefix': '/learn/notes',
    'enabled': True
}

def setup_module(app):
    from . import routes

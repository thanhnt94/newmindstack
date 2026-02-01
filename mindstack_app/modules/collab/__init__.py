# File: mindstack_app/modules/collab/__init__.py
from flask import Blueprint

blueprint = Blueprint('collab', __name__)

module_metadata = {
    'name': 'Học nhóm',
    'icon': 'users',
    'category': 'Learning',
    'url_prefix': '/learn/collab',
    'enabled': True
}

def setup_module(app):
    from . import routes

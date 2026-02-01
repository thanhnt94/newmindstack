# File: mindstack_app/modules/chat/__init__.py
from flask import Blueprint

blueprint = Blueprint('chat', __name__)

module_metadata = {
    'name': 'Chat',
    'icon': 'message-square',
    'category': 'Collaboration',
    'url_prefix': '/chat',
    'enabled': True
}

def setup_module(app):
    from . import routes

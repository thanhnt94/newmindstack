# File: mindstack_app/modules/feedback/__init__.py
from flask import Blueprint

blueprint = Blueprint('feedback', __name__)

module_metadata = {
    'name': 'Phản hồi',
    'icon': 'message-circle',
    'category': 'System',
    'url_prefix': '/feedback',
    'enabled': True
}

def setup_module(app):
    from . import routes

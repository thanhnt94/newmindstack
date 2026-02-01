
# File: mindstack_app/modules/session/__init__.py
from flask import Blueprint

blueprint = Blueprint('session', __name__)

# Module Metadata
module_metadata = {
    'name': 'Quản lý Phiên học',
    'icon': 'clock-rotate-left',
    'category': 'Core',
    'url_prefix': '/session',
    'admin_route': None,
    'enabled': True
}

def setup_module(app):
    """Register routes for the session module."""
    from . import routes

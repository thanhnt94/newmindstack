from flask import Blueprint

blueprint = Blueprint('learning_history', __name__)

module_metadata = {
    'name': 'Lịch sử học tập',
    'icon': 'clock-rotate-left',
    'category': 'Core',
    'url_prefix': '/history',
    'admin_route': None,
    'enabled': True
}

def setup_module(app):
    """Register module."""
    # Register models immediately to ensure they are picked up by migrations
    from . import models

# File: mindstack_app/modules/learning/__init__.py
# Forced reload learning
from flask import Blueprint

learning_bp = Blueprint('learning', __name__)

module_metadata = {
    'name': 'Quản lý Học tập',
    'icon': 'graduation-cap',
    'category': 'Learning',
    'url_prefix': '/learn',
    'admin_route': 'session.manage_sessions',
    'enabled': True
}

def setup_module(app):
    """Register routes for the learning module."""
    from . import routes

# File: mindstack_app/modules/quiz/__init__.py
from flask import Blueprint

quiz_bp = Blueprint('quiz', __name__)

# Module Metadata
module_metadata = {
    'name': 'Hệ thống Quiz',
    'icon': 'circle-question',
    'category': 'Learning',
    'url_prefix': '/learn/quiz',
    'admin_route': 'quiz.dashboard',
    'enabled': True
}

def setup_module(app):
    """Register routes for the quiz module."""
    # Deferred import to avoid circular dependencies
    from . import routes

"""Quiz module containing individual and battle modes."""

from flask import Blueprint

blueprint = Blueprint('quiz', __name__)

# Module Metadata
module_metadata = {
    'name': 'Quizzes',
    'icon': 'circle-question',
    'category': 'Learning',
    'url_prefix': '/learn/quiz',
    'enabled': True
}

def setup_module(app):
    """Register routes for the quiz module."""
    from . import routes

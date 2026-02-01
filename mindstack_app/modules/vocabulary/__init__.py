# File: mindstack_app/modules/vocabulary/__init__.py
from flask import Blueprint

vocabulary_bp = Blueprint('vocabulary', __name__)

# Module Metadata
module_metadata = {
    'name': 'Học từ vựng (Vocab Hub)',
    'icon': 'book-open',
    'category': 'Learning',
    'url_prefix': '/learn/vocabulary',
    'enabled': True
}

def setup_module(app):
    """Register routes for the vocabulary module."""
    # Deferred import to avoid circular dependencies
    from . import routes
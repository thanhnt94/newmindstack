"""Vocabulary Learning Hub: Consolidated multiple learning modes."""

from .routes import blueprint

# Module Metadata
module_metadata = {
    'name': 'Vocabulary',
    'icon': 'book-open',
    'category': 'Learning',
    'url_prefix': '/learn/vocabulary',
    'enabled': True
}

def setup_module(app):
    """Register routes for the vocabulary module."""
    from . import routes

# File: mindstack_app/modules/vocabulary/__init__.py
from flask import Blueprint

vocabulary_bp = Blueprint('vocabulary', __name__)

# Module Metadata
module_metadata = {
    'name': 'Học từ vựng (Vocab Hub)',
    'icon': 'book-open',
    'category': 'Learning',
    'url_prefix': '/learn/vocabulary',
    'admin_route': None, # Managed via content_management or flashcard dashboard
    'enabled': True
}

def setup_module(app):
    """Standard module setup."""
    # Importing routes attaches them to the vocabulary_bp
    from . import routes
    
    # Register Signals, Context Processors, etc.
    @app.context_processor
    def inject_vocab_metadata():
        return {'vocab_module': module_metadata}
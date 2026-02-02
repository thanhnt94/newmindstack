"""Flashcard module: Core engine and SRS logic."""

from flask import Blueprint

blueprint = Blueprint('vocab_flashcard', __name__)

# Module Metadata for Admin Panel
module_metadata = {
    'name': 'Flashcards',
    'icon': 'clone',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-flashcard',
    'admin_route': 'vocab_flashcard.dashboard_home',
    'enabled': True
}

_setup_done = False

def setup_module(app):
    global _setup_done
    if _setup_done:
        return
    _setup_done = True
    
    # Register the main blueprint
    from . import routes
    app.register_blueprint(blueprint, url_prefix=module_metadata['url_prefix'])
    
    # Additional setup (signals, etc.) can go here
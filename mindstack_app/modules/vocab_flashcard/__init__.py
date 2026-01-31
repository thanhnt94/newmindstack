"""Flashcard module: Core engine and SRS logic."""

from flask import Blueprint

blueprint = Blueprint('vocab_flashcard', __name__)

# Module Metadata for Admin Panel
module_metadata = {
    'name': 'Flashcards',
    'icon': 'clone',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-flashcard',
    'admin_route': 'vocab_flashcard.dashboard.dashboard_home',
    'enabled': True
}

def setup_module(app):
    """Register sub-blueprints for the flashcard module."""
    from .routes.dashboard import dashboard_bp
    from .routes.views import flashcard_learning_bp
    from .routes.collab import flashcard_collab_bp
    
    blueprint.register_blueprint(dashboard_bp)
    blueprint.register_blueprint(flashcard_learning_bp)
    blueprint.register_blueprint(flashcard_collab_bp)

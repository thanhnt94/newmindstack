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
    # Deferred imports to avoid circular dependencies
    from .routes.dashboard import dashboard_bp
    from .routes.bp import flashcard_learning_bp
    from .routes import views  # Trigger route registration
    from .routes.collab import flashcard_collab_bp
    from .routes import api_bp
    
    blueprint.register_blueprint(dashboard_bp)
    blueprint.register_blueprint(flashcard_learning_bp)
    blueprint.register_blueprint(flashcard_collab_bp)
    blueprint.register_blueprint(api_bp)
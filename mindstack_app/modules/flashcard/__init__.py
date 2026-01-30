"""Flashcard module: Core engine and SRS logic."""

from flask import Blueprint

blueprint = Blueprint('flashcard', __name__)

# Module Metadata for Admin Panel
module_metadata = {
    'name': 'Flashcards',
    'icon': 'clone',
    'category': 'Learning',
    'url_prefix': '/learn/flashcard',
    'admin_route': 'flashcard.dashboard.dashboard_home',
    'enabled': True
}

def setup_module(app):
    """Register sub-blueprints for the flashcard module."""
    from .dashboard import dashboard_bp
    from .individual import flashcard_learning_bp
    from .collab.routes import flashcard_collab_bp
    
    blueprint.register_blueprint(dashboard_bp)
    blueprint.register_blueprint(flashcard_learning_bp)
    blueprint.register_blueprint(flashcard_collab_bp)
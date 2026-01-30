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
    """Register sub-blueprints for the vocabulary module."""
    from .mcq import mcq_bp
    from .typing import typing_bp
    from .matching import matching_bp
    from .speed import speed_bp
    from .listening import listening_bp

    blueprint.register_blueprint(mcq_bp)
    blueprint.register_blueprint(typing_bp)
    blueprint.register_blueprint(matching_bp)
    blueprint.register_blueprint(speed_bp, url_prefix='/speed')
    blueprint.register_blueprint(listening_bp, url_prefix='/listening')

# File: mindstack_app/modules/learning/vocabulary/__init__.py
# Vocabulary Learning Hub Module
# Refactored to use routes/ package structure

# Import blueprint from routes package
from .routes import vocabulary_bp

# Import and register submodules
from .mcq import mcq_bp
from .typing import typing_bp
from .matching import matching_bp
from .speed import speed_bp
from .listening import listening_bp

# Register submodule blueprints
vocabulary_bp.register_blueprint(mcq_bp, url_prefix='/mcq')
vocabulary_bp.register_blueprint(typing_bp, url_prefix='/typing')
vocabulary_bp.register_blueprint(matching_bp, url_prefix='/matching')
vocabulary_bp.register_blueprint(speed_bp, url_prefix='/speed')
vocabulary_bp.register_blueprint(listening_bp, url_prefix='/listening')

__all__ = ['vocabulary_bp']

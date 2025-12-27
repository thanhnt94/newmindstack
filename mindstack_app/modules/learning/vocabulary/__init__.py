# File: mindstack_app/modules/learning/vocabulary/__init__.py
# Vocabulary Learning Hub Module

from flask import Blueprint

vocabulary_bp = Blueprint(
    'vocabulary',
    __name__,
    url_prefix='/vocabulary',
    template_folder='templates'
)

# Import and register submodules
# from .flashcard import vocab_flashcard_bp
from .mcq import mcq_bp
from .typing import typing_bp
from .matching import matching_bp
from .speed import speed_bp

# vocabulary_bp.register_blueprint(vocab_flashcard_bp, url_prefix='/flashcard')
vocabulary_bp.register_blueprint(mcq_bp, url_prefix='/mcq')
vocabulary_bp.register_blueprint(typing_bp, url_prefix='/typing')
vocabulary_bp.register_blueprint(matching_bp, url_prefix='/matching')
vocabulary_bp.register_blueprint(speed_bp, url_prefix='/speed')

from . import routes


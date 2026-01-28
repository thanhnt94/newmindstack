"""Shared Flashcard module definitions."""

from flask import Blueprint

flashcard_bp = Blueprint(
    'flashcard', __name__, url_prefix='/flashcard'
)

# Register sub-blueprints
from .dashboard import dashboard_bp
flashcard_bp.register_blueprint(dashboard_bp)

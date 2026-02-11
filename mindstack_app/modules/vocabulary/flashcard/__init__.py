"""Flashcard sub-package within vocabulary module."""

from flask import Blueprint

# Sub-blueprint keeps the SAME name as the old module
# so all url_for('vocab_flashcard.xxx') calls in templates continue to work.
flashcard_bp = Blueprint('vocab_flashcard', __name__)

def register_flashcard_routes():
    """Import routes to attach them to the blueprint."""
    from .routes import views, api

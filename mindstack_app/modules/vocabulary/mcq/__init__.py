"""MCQ sub-package within vocabulary module."""

from flask import Blueprint

# Sub-blueprint keeps the SAME name as the old module
mcq_bp = Blueprint('vocab_mcq', __name__)

def register_mcq_routes():
    """Import routes to attach them to the blueprint."""
    from .routes import views

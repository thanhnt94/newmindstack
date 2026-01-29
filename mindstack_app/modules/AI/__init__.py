"""AI Module Entry Point."""
from flask import Blueprint

# Blueprint for the AI module features
ai_bp = Blueprint('AI', __name__)

def setup_module(app):
    """Module-level infrastructure setup."""
    from .services.ai_service import setup_ai_signals
    setup_ai_signals(app)

# Register routes
from . import routes
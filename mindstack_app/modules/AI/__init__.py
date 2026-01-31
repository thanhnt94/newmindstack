# File: mindstack_app/modules/AI/__init__.py
from flask import Blueprint

blueprint = Blueprint('AI', __name__)

module_metadata = {
    'name': 'AI Coach',
    'icon': 'robot',
    'category': 'Learning',
    'url_prefix': '/learn/ai',
    'enabled': True
}

def setup_module(app):
    """Module-level infrastructure setup."""
    from .services.ai_service import setup_ai_signals
    setup_ai_signals(app)
    
    # Register routes and events
    from . import routes, events
    from .routes.admin import admin_bp
    app.register_blueprint(admin_bp)

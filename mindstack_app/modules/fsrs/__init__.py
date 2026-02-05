from flask import Blueprint

fsrs_bp = Blueprint('fsrs', __name__)

module_metadata = {
    'name': 'Thuật toán FSRS',
    'icon': 'brain',
    'category': 'System',
    'url_prefix': '/admin/fsrs',
    'admin_route': 'fsrs.config_page',
    'enabled': True
}

def setup_module(app):
    """Initialize the FSRS module."""
    from . import models
    from .routes.api import api_bp
    # Import admin_views to ensure routes are registered to fsrs_bp
    from .routes import admin_views

    # Register API routes
    app.register_blueprint(api_bp)
    
    # Register Admin/View routes
    # specific handling: bootstrap.py handles fsrs_bp registration via module_metadata
    # app.register_blueprint(fsrs_bp)
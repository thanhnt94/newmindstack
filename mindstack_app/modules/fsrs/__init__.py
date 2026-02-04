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
    from .routes.admin_views import fsrs_bp as admin_views_bp

    # Register API routes
    app.register_blueprint(api_bp)
    
    # Register Admin/View routes
    # Note: 'fsrs_bp' defined at module level is often used for templates in older structure.
    # We ensure the admin views are registered.
    app.register_blueprint(admin_views_bp)
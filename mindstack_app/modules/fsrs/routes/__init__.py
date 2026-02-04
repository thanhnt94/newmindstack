from flask import Blueprint
from .api import api_bp
from .admin_views import fsrs_bp as admin_bp

def init_routes(app):
    """Register blueprints for the FSRS module."""
    # Register the JSON API Blueprint
    app.register_blueprint(api_bp)
    
    # Register the Admin/HTML Blueprint (if not already handled separately)
    # The original __init__.py registered 'routes', but admin_views defines 'fsrs_bp'.
    # We'll expose them here for the main setup_module to consume if needed,
    # or rely on the standard pattern.
    pass
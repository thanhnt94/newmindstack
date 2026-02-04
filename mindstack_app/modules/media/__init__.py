# File: mindstack_app/modules/media/__init__.py
"""
Media Module
============
Centralized media handling for the application.
Manages image search, caching, and cleanup operations.
"""

from flask import Blueprint

blueprint = Blueprint(
    'media',
    __name__,
    url_prefix='/api/media'
)

module_metadata = {
    'name': 'Media',
    'icon': 'fa-image',
    'description': 'Centralized media operations (image search, cache)',
    'url_prefix': '/api/media',
    'order': 99,
    'is_visible': False  # Internal module, no UI
}

def setup_module(app):
    """Register media module with the Flask app."""
    app.register_blueprint(blueprint)

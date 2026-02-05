from flask import Blueprint

module_metadata = {
    "name": "Content Generator",
    "key": "content_generator",
    "description": "Centralized AI, Audio, and Image generation factory.",
    "icon": "fa-robot",
    "version": "1.0.0",
    "author": "System",
    "url_prefix": "/admin/content-generator",
    "enabled": True,
    "required_modules": []
}

# Use 'blueprint' to match ModuleDefinition in module_registry.py
blueprint = Blueprint("content_generator", __name__, template_folder="templates", static_folder="static")

def setup_module(app):
    """
    Setup function called by the application factory to register the module.
    """
    # Import routes to register endpoints (Presentation Layer)
    from .routes import api, views
    
    # Import events to register listeners (Event Layer)
    from . import events
    
    # Note: Registration is handled by core/bootstrap.py load_modules
    # or core/module_registry.py register_modules. 
    # Manual registration here is a fallback.
    if "content_generator" not in app.blueprints:
        app.register_blueprint(blueprint, url_prefix=module_metadata["url_prefix"])
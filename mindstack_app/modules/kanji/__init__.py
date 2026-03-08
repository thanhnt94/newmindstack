from flask import Blueprint
from .routes.api import kanji_api_bp

# Define views blueprint here to ensure static_folder is correct
blueprint = Blueprint('kanji_views', __name__, static_folder='static')

def setup_module(app):
    """
    Register the Kanji module blueprints.
    """
    # Import to register routes on the blueprint
    from .routes import views  
    
    # We manually register the API blueprint. 
    # The main 'blueprint' (views) will be automatically registered by bootstrap.py
    app.register_blueprint(kanji_api_bp)

module_metadata = {
    "name": "Kanji",
    "key": "kanji",
    "icon": "fas fa-characters",
    "description": "Kanji decomposition and similarity analysis.",
    "url_prefix": "/kanji"
}

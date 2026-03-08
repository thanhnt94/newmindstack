from flask import Blueprint
from .routes.api import kanji_api_bp

# Define views blueprint here to ensure static_folder is correct
kanji_views_bp = Blueprint('kanji_views', __name__, static_folder='static')

def setup_module(app):
    """
    Register the Kanji module blueprints.
    """
    from .routes import views  # Import to register routes on the blueprint
    
    app.register_blueprint(kanji_api_bp)
    app.register_blueprint(kanji_views_bp)

module_metadata = {
    "name": "Kanji",
    "key": "kanji",
    "icon": "fas fa-characters",
    "description": "Kanji decomposition and similarity analysis.",
    "url_prefix": "/kanji"
}

# mindstack_app/modules/session_hub/__init__.py
from flask import Blueprint

session_hub_bp = Blueprint('session_hub', __name__, template_folder='templates')

# Module Metadata for Discovery
module_metadata = {
    'name': 'Session Hub',
    'icon': 'chart-line',
    'category': 'Analysis',
    'url_prefix': '/session-hub',
    'enabled': True
}

def setup_module(app):
    """Setup logic for the Session Hub module."""
    from . import routes

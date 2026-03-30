from flask import Blueprint

blueprint = Blueprint('auth_center', __name__)

from . import routes

module_metadata = {
    'name': 'Hệ sinh thái SSO',
    'icon': 'hub',
    'category': 'System',
    'url_prefix': '/auth-center',
    'enabled': True
}

def setup_module(app):
    """
    Initial configuration when the module is loaded by the Core Bootstrap.
    """
    app.logger.info(f"Central Auth Module handshake initialized for {module_metadata['name']}")

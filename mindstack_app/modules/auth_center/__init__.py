from flask import Blueprint

# 1. Main Blueprint: Prefix with /auth-center for SSO Login/Callback UI
blueprint = Blueprint('auth_center', __name__)

# 2. Ecosystem Sync Blueprint: Root-level for CentralAuth Discovery
internal_sync_bp = Blueprint('internal_sync', __name__)

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
    
    # Manually register the internal sink blueprint WITHOUT prefix
    if internal_sync_bp.name not in app.blueprints:
        app.register_blueprint(internal_sync_bp)
        app.logger.info("Modular Sync API: internal_sync registered at root")
        
    # Ensure CSRF exemption
    try:
        from mindstack_app.core.extensions import csrf_protect
        csrf_protect.exempt(internal_sync_bp)
    except Exception as e:
        app.logger.error(f"Failed to exempt modular sync-api from CSRF: {e}")

# File: mindstack_app/modules/notification/__init__.py
from flask import Blueprint

blueprint = Blueprint('notification', __name__)

module_metadata = {
    'name': 'Thông báo',
    'icon': 'bell',
    'category': 'System',
    'url_prefix': '/notifications',
    'enabled': True
}

def setup_module(app):
    from . import routes
    
    # Register event listeners for signal-based notifications
    from .services.notification_manager import NotificationManager
    NotificationManager.init_listeners()

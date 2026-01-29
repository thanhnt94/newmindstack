from flask import Blueprint

notification_bp = Blueprint('notification', __name__,
                           url_prefix='/notifications')

from . import routes

# Register event listeners for signal-based notifications
from .services.notification_manager import NotificationManager

# Initialize listeners
NotificationManager.init_listeners()


from flask import Blueprint

notification_bp = Blueprint('notification', __name__,
                           url_prefix='/notifications')

from . import routes

# Register event listeners for signal-based notifications
from . import events  # noqa: E402, F401

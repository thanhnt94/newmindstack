from flask import Blueprint

notification_bp = Blueprint('notification', __name__, 
                           template_folder='templates',
                           url_prefix='/notifications')

from . import routes

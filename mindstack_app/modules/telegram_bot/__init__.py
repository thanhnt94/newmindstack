from flask import Blueprint

telegram_bot_bp = Blueprint('telegram_bot', __name__, url_prefix='/telegram')

from . import routes

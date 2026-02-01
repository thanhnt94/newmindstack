# File: mindstack_app/modules/telegram_bot/__init__.py
from flask import Blueprint

blueprint = Blueprint('telegram_bot', __name__)

module_metadata = {
    'name': 'Telegram Bot',
    'icon': 'send',
    'category': 'System',
    'url_prefix': '/telegram',
    'enabled': True
}

def setup_module(app):
    from . import routes

# File: mindstack_app/modules/user_profile/__init__.py
from flask import Blueprint

blueprint = Blueprint('user_profile', __name__)

module_metadata = {
    'name': 'Hồ sơ cá nhân',
    'icon': 'user',
    'category': 'System',
    'url_prefix': '/profile',
    'enabled': True
}

def setup_module(app):
    from . import routes

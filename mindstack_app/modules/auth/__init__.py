# File: mindstack_app/modules/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

module_metadata = {
    'name': 'Xác thực',
    'icon': 'lock',
    'category': 'System',
    'url_prefix': '/auth',
    'enabled': True
}

def setup_module(app):
    from . import routes
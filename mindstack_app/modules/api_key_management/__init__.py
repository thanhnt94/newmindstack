# File: mindstack_app/modules/api_key_management/__init__.py
from flask import Blueprint

blueprint = Blueprint('api_key_management', __name__)

module_metadata = {
    'name': 'Quản lý API Key',
    'icon': 'key',
    'category': 'System',
    'url_prefix': '/admin/api-keys',
    'admin_route': 'api_key_management.list_api_keys',
    'enabled': True
}

def setup_module(app):
    from . import routes

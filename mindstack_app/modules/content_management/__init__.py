# File: mindstack_app/modules/content_management/__init__.py
from flask import Blueprint

blueprint = Blueprint('content_management', __name__)

module_metadata = {
    'name': 'Quản lý nội dung',
    'icon': 'layer-group',
    'category': 'System',
    'url_prefix': '/content/manage',
    'admin_route': 'content_management.content_dashboard',
    'enabled': True
}

def setup_module(app):
    from . import routes

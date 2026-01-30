# File: mindstack_app/modules/admin/__init__.py
from flask import Blueprint
from .context_processors import admin_context_processor

blueprint = Blueprint('admin', __name__)
blueprint.app_context_processor(admin_context_processor)

module_metadata = {
    'name': 'Quản trị hệ thống',
    'icon': 'cogs',
    'category': 'System',
    'url_prefix': '/admin',
    'admin_route': 'admin.admin_dashboard',
    'enabled': True
}

def setup_module(app):
    from . import routes

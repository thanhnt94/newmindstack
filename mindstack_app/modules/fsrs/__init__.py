# File: mindstack_app/modules/fsrs/__init__.py
from flask import Blueprint

fsrs_bp = Blueprint('fsrs', __name__)

module_metadata = {
    'name': 'Thuật toán FSRS',
    'icon': 'brain',
    'category': 'System',
    'url_prefix': '/admin/fsrs',
    'admin_route': 'fsrs.config_page',
    'enabled': True
}

def setup_module(app):
    from . import models, routes

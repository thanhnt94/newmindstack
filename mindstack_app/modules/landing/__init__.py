# File: mindstack_app/modules/landing/__init__.py
from flask import Blueprint

blueprint = Blueprint('landing', __name__)

module_metadata = {
    'name': 'Trang chủ',
    'icon': 'home',
    'category': 'System',
    'enabled': True
}

def setup_module(app):
    from . import routes

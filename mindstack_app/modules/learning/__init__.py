# File: mindstack_app/modules/learning/__init__.py
from flask import Blueprint

blueprint = Blueprint('learning', __name__)

module_metadata = {
    'name': 'Học tập',
    'icon': 'graduation-cap',
    'category': 'Learning',
    'url_prefix': '/learn',
    'enabled': True
}

def setup_module(app):
    from . import routes

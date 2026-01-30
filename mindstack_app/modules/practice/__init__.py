# File: mindstack_app/modules/practice/__init__.py
from flask import Blueprint

blueprint = Blueprint('practice', __name__)

module_metadata = {
    'name': 'Luyện tập',
    'icon': 'dumbbell',
    'category': 'Learning',
    'url_prefix': '/learn/practice',
    'enabled': True
}

def setup_module(app):
    from . import routes

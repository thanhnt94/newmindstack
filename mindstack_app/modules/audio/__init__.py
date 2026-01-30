# File: mindstack_app/modules/audio/__init__.py
from flask import Blueprint

blueprint = Blueprint('audio', __name__)

module_metadata = {
    'name': 'Audio Studio',
    'icon': 'volume-up',
    'category': 'System',
    'url_prefix': '/admin/audio',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from . import events

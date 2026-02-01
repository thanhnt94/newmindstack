from flask import Blueprint

blueprint = Blueprint('vocab_speed', __name__)

# Module Metadata
module_metadata = {
    'name': 'Vocabulary Speed',
    'icon': 'bolt',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-speed',
    'enabled': True
}

def setup_module(app):
    from . import routes

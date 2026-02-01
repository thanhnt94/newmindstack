from flask import Blueprint

blueprint = Blueprint('vocab_typing', __name__)

# Module Metadata
module_metadata = {
    'name': 'Vocabulary Typing',
    'icon': 'keyboard',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-typing',
    'enabled': True
}

def setup_module(app):
    from . import routes

from flask import Blueprint

blueprint = Blueprint('vocab_listening', __name__)

# Module Metadata
module_metadata = {
    'name': 'Vocabulary Listening',
    'icon': 'headphones',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-listening',
    'enabled': True
}

def setup_module(app):
    from . import routes

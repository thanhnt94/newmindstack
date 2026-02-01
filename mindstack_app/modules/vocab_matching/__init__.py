from flask import Blueprint

blueprint = Blueprint('vocab_matching', __name__)

# Module Metadata
module_metadata = {
    'name': 'Vocabulary Matching',
    'icon': 'puzzle-piece',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-matching',
    'enabled': True
}

def setup_module(app):
    from . import routes

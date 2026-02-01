from flask import Blueprint

blueprint = Blueprint('vocab_mcq', __name__)

# Module Metadata
module_metadata = {
    'name': 'Vocabulary MCQ',
    'icon': 'th-list',
    'category': 'Learning',
    'url_prefix': '/learn/vocab-mcq',
    'enabled': True
}

def setup_module(app):
    from . import routes
    # Registration logic if needed

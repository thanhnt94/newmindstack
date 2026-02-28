# mindstack_app/modules/vocab_hub/__init__.py
from flask import Blueprint

vocab_hub_bp = Blueprint('vocab_hub', __name__, template_folder='templates')

# Module Metadata for Discovery
module_metadata = {
    'name': 'Vocab Hub',
    'icon': 'chart-pie',
    'category': 'Analysis',
    'url_prefix': '/learn/vocab-hub',
    'enabled': True
}

def setup_module(app):
    """Setup logic for the Vocab Hub module."""
    from . import routes
    # Note: bootstrap.py will register the blueprint using url_prefix from metadata
    
    # Register any event listeners or signals if needed
    from . import events

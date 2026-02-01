# File: mindstack_app/modules/audio/__init__.py
from flask import Blueprint

audio_bp = Blueprint('audio', __name__)

module_metadata = {
    'name': 'Audio Studio',
    'icon': 'microphone-lines',
    'category': 'System',
    'url_prefix': '/admin/audio',
    'admin_route': 'audio.admin_audio_studio',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from . import events

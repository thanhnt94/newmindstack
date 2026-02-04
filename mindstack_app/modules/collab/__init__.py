# File: mindstack_app/modules/collab/__init__.py
"""Collab Module - Collaborative Learning Features.

This module contains all room-based collaborative learning functionality:
- Flashcard Collab (group flashcard study)
- Quiz Battle (multiplayer quiz competition)
"""

from flask import Blueprint

blueprint = Blueprint('collab', __name__)

module_metadata = {
    'name': 'Học nhóm',
    'icon': 'users',
    'category': 'Learning',
    'url_prefix': '/learn/collab',
    'enabled': True
}

def setup_module(app):
    # Import models to register with SQLAlchemy
    from . import models  # noqa: F401
    from . import routes

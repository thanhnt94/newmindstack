# Collab Module
# Entry point for collaborative learning modes (Quiz Battle, Flashcard Collab).
# This module provides a unified dashboard for all collaboration features.

from flask import Blueprint

collab_bp = Blueprint(
    'collab', 
    __name__, 
    url_prefix='/collab'
)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402, F401

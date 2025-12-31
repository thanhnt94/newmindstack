# Practice Module
# Entry point for flashcard practice modes.
# Supports single-set and multi-set practice by calling the flashcard engine.

from flask import Blueprint

practice_bp = Blueprint(
    'practice', 
    __name__, 
    url_prefix='/practice'
)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402, F401

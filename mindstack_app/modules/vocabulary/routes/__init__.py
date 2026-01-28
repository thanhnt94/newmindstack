# File: vocabulary/routes/__init__.py
# Vocabulary Module - Routes Package (following quiz/individual/routes pattern)

from flask import Blueprint

# Create blueprint
vocabulary_bp = Blueprint(
    'vocabulary',
    __name__,
    url_prefix='/vocabulary'
)

# Import route handlers (this registers the routes with the blueprint)
from . import dashboard, api, flashcard_session  # noqa: E402,F401

# File: vocabulary/typing/__init__.py
# Typing Learning Mode Module

from flask import Blueprint

typing_bp = Blueprint(
    'vocab_typing',
    __name__,
    url_prefix='/typing'
)

from . import routes

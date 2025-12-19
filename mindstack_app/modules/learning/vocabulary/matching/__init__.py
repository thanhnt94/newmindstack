# File: vocabulary/matching/__init__.py
# Matching Learning Mode Module

from flask import Blueprint

matching_bp = Blueprint(
    'vocab_matching',
    __name__,
    url_prefix='/matching',
    template_folder='templates'
)

from . import routes

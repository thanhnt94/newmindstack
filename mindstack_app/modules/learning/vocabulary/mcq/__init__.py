# File: vocabulary/mcq/__init__.py
# MCQ Learning Mode Module

from flask import Blueprint

mcq_bp = Blueprint(
    'vocab_mcq',
    __name__,
    url_prefix='/mcq',
    template_folder='templates'
)

from . import routes

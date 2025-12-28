# File: vocabulary/speed/__init__.py
# Speed Review Learning Mode Module

from flask import Blueprint

speed_bp = Blueprint(
    'vocab_speed',
    __name__,
    url_prefix='/speed',
    template_folder='templates'
)

from . import routes

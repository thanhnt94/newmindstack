# File: vocabulary/speed/__init__.py
# Speed Review Learning Mode Module

from flask import Blueprint

speed_bp = Blueprint(
    'vocab_speed',
    __name__
)

from . import routes

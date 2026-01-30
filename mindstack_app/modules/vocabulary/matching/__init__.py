# File: vocabulary/matching/__init__.py
# Matching Learning Mode Module

from flask import Blueprint

matching_bp = Blueprint('matching', __name__)

from . import routes

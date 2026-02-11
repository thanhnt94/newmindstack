"""Matching sub-package within vocabulary module."""

from flask import Blueprint

matching_bp = Blueprint('vocab_matching', __name__)

def register_matching_routes():
    from .routes import views

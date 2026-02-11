"""Typing sub-package within vocabulary module."""

from flask import Blueprint

typing_bp = Blueprint('vocab_typing', __name__)

def register_typing_routes():
    from .routes import views

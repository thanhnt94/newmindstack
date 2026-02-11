"""Listening sub-package within vocabulary module."""

from flask import Blueprint

listening_bp = Blueprint('vocab_listening', __name__)

def register_listening_routes():
    from .routes import views

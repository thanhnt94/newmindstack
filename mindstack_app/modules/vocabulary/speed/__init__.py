"""Speed sub-package within vocabulary module."""

from flask import Blueprint

speed_bp = Blueprint('vocab_speed', __name__)

def register_speed_routes():
    from .routes import views

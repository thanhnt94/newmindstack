from flask import Blueprint

listening_bp = Blueprint(
    'listening',
    __name__,
    url_prefix='/learn/vocabulary/listening'
)

from . import routes

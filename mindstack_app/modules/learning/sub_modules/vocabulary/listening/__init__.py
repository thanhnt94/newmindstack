from flask import Blueprint

listening_bp = Blueprint(
    'listening',
    __name__
)

from . import routes

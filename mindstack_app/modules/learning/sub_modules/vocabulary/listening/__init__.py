from flask import Blueprint

listening_bp = Blueprint(
    'listening',
    __name__,
    template_folder='templates',
    url_prefix='/learn/vocabulary/listening'
)

from . import routes

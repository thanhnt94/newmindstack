from flask import Blueprint

gamification_bp = Blueprint(
    'gamification',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/gamification'
)

gamification_api_bp = Blueprint(
    'gamification_api',
    __name__,
    url_prefix='/api/gamification'
)

from . import routes

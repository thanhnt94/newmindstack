from flask import Blueprint

analytics_bp = Blueprint(
    'analytics',
    __name__,
    # template_folder='templates',  # Moved to global templates/v3/pages/analytics
    static_folder='static',
    url_prefix='/analytics'
)

from .routes import *

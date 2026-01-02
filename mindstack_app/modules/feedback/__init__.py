from flask import Blueprint

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')

from . import routes
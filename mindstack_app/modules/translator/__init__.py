from flask import Blueprint

translator_bp = Blueprint('translator', __name__, url_prefix='/translator', static_folder='static')

from . import routes

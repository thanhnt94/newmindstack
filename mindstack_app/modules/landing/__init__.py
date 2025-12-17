from flask import Blueprint

landing_bp = Blueprint('landing', __name__, template_folder='templates')

from . import routes

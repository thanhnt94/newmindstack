from flask import Blueprint

memrise_bp = Blueprint('vocab_memrise', __name__, template_folder='templates', url_prefix='/learning/vocabulary/memrise')

from . import routes

from flask import Blueprint

blueprint = Blueprint('vocabulary', __name__)

from . import api, dashboard

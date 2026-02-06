from flask import Blueprint

blueprint = Blueprint(
    'access_control', 
    __name__, 
    url_prefix='/api/access-control'
)

from . import api

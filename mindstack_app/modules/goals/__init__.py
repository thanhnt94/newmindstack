"""Blueprint registration for the goals module."""

from flask import Blueprint

blueprint = Blueprint('goals', __name__)

module_metadata = {
    'name': 'Mục tiêu',
    'icon': 'target',
    'category': 'Learning',
    'enabled': True
}

def setup_module(app):
    from . import routes

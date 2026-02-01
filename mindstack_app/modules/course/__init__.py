# File: mindstack_app/modules/course/__init__.py
from flask import Blueprint

blueprint = Blueprint('course', __name__)

module_metadata = {
    'name': 'Khóa học',
    'icon': 'graduation-cap',
    'category': 'Learning',
    'url_prefix': '/learn/course',
    'enabled': True
}

def setup_module(app):
    from . import routes

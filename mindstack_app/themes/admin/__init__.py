# File: mindstack_app/themes/admin/__init__.py
from flask import Blueprint

blueprint = Blueprint(
    'admin_theme',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/admin'
)

# File: mindstack_app/themes/aura_mobile/__init__.py
from flask import Blueprint

blueprint = Blueprint(
    'aura_mobile',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/aura_mobile'
)

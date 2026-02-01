# File: mindstack_app/modules/dashboard/__init__.py
from flask import Blueprint

blueprint = Blueprint('dashboard', __name__)

module_metadata = {
    'name': 'Bảng điều khiển',
    'icon': 'home',
    'category': 'System',
    'enabled': True
}

def setup_module(app):
    # Chỉ cần import routes là đủ để decorator @blueprint.route thực thi
    from . import routes

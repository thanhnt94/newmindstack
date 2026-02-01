# File: mindstack_app/modules/gamification/__init__.py
from flask import Blueprint

blueprint = Blueprint('gamification', __name__)

module_metadata = {
    'name': 'Game hóa (Hệ thống điểm)',
    'icon': 'medal',
    'category': 'System',
    'url_prefix': '/admin/gamification',
    'admin_route': 'gamification.list_badges',
    'enabled': True
}

def setup_module(app):
    from . import routes
    from .services.reward_manager import RewardManager
    RewardManager.init_listeners()

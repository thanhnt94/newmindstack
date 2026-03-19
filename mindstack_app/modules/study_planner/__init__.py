"""Study Planner module - Lập kế hoạch học tập theo mục tiêu thời gian."""

from flask import Blueprint

study_planner_bp = Blueprint('study_planner', __name__)

module_metadata = {
    'name': 'Lập kế hoạch học tập',
    'icon': 'calendar-alt',
    'category': 'Learning',
    'url_prefix': '/planner',
    'enabled': True
}


def setup_module(app):
    from . import routes
    from . import events  # Register signal listeners

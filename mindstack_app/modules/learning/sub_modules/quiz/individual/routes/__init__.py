# Quiz Individual Module - Routes Package

from flask import Blueprint
import os
from jinja2 import ChoiceLoader, FileSystemLoader

# Get template paths
_module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_individual_templates_path = os.path.join(_module_dir, 'templates')
_shared_quiz_templates_path = os.path.join(os.path.dirname(_module_dir), 'templates')
_battle_templates_path = os.path.join(os.path.dirname(_module_dir), 'battle', 'templates')

# Get static path
_static_path = os.path.join(_module_dir, 'static')

# Create blueprint
quiz_learning_bp = Blueprint(
    'quiz_learning',
    __name__,
    static_folder=_static_path,
    static_url_path='/quiz_learning/static'
)

# Setup template loader to search multiple directories
quiz_learning_bp.jinja_loader = ChoiceLoader([
    FileSystemLoader(_individual_templates_path),
    FileSystemLoader(_shared_quiz_templates_path),
    FileSystemLoader(_battle_templates_path),
])

# Import route handlers
from . import main, api  # noqa: E402,F401

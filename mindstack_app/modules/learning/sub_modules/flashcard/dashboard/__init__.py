from flask import Blueprint
import os

# Define the blueprint for the flashcard dashboard
# Template folder is local to this submodule: ./templates
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')

dashboard_bp = Blueprint(
    'flashcard_dashboard',
    __name__,
    template_folder=template_dir,
    # Url prefix handled by parent or registration
)

from . import routes

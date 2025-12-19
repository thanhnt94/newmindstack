# File: vocabulary/flashcard/__init__.py
# Flashcard Learning Mode - Integrated into Vocabulary Hub

from flask import Blueprint
import os

# Template folder is in parent vocabulary templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(base_dir, 'templates')

# Create blueprint with unique name for vocabulary context
vocab_flashcard_bp = Blueprint(
    'vocab_flashcard',
    __name__,
    template_folder=template_dir,
    static_folder='static',
    static_url_path='/vocab_flashcard_static'
)

from . import routes  # noqa: E402,F401
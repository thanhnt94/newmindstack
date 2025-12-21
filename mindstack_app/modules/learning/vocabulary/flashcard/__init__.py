# File: vocabulary/flashcard/__init__.py
# Flashcard Learning Mode - Integrated into Vocabulary Hub

from flask import Blueprint
import os

# Template folder points to learning/flashcard/templates 
# (which contains both session and setup templates)
module_dir = os.path.dirname(os.path.abspath(__file__))
# Go up to vocabulary, then up to learning, then to flashcard/templates
learning_dir = os.path.dirname(os.path.dirname(module_dir))
template_dir = os.path.join(learning_dir, 'flashcard', 'templates')

# Create blueprint with unique name for vocabulary context
vocab_flashcard_bp = Blueprint(
    'vocab_flashcard',
    __name__,
    template_folder=template_dir,
    static_folder='static',
    static_url_path='/vocab_flashcard_static'
)

from . import routes  # noqa: E402,F401
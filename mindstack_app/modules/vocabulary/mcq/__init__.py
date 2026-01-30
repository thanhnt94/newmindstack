# File: vocabulary/mcq/__init__.py
# MCQ (Multiple Choice Quiz) Learning Mode for Vocabulary

from flask import Blueprint

mcq_bp = Blueprint('mcq', __name__)

from . import routes

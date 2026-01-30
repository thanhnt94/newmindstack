"""Quiz module containing individual and battle modes."""

from flask import Blueprint

blueprint = Blueprint('quiz', __name__)

# Module Metadata
module_metadata = {
    'name': 'Quizzes',
    'icon': 'circle-question',
    'category': 'Learning',
    'url_prefix': '/learn/quiz',
    'enabled': True
}

def setup_module(app):
    """Register sub-blueprints for the quiz module."""
    from .individual import quiz_learning_bp
    from .battle.routes import quiz_battle_bp
    
    blueprint.register_blueprint(quiz_learning_bp)
    blueprint.register_blueprint(quiz_battle_bp)
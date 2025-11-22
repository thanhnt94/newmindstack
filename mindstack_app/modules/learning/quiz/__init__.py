"""Quiz module containing individual and battle modes."""

from .individual.routes import quiz_learning_bp
from .battle.routes import quiz_battle_bp

__all__ = ["quiz_learning_bp", "quiz_battle_bp"]

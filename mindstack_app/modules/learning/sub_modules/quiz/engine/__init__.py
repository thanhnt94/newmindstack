# Quiz Engine Module
# Core logic for quiz/MCQ learning.
# Supports single-set, multi-set, single question, batch mode, and battle.

from .core import QuizEngine
from .config import QuizConfig

__all__ = [
    'QuizEngine',
    'QuizConfig',
]

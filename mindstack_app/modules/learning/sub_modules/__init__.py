"""
Learning Sub-Modules

Feature modules for different learning modes:
- vocabulary: Vocabulary learning with multiple modes
- flashcard: Standalone flashcard system
- quiz: Quiz and assessment
- course: Course management
- practice: Practice sessions
- collab: Collaborative learning
"""

# Convenience imports for blueprints
from .vocabulary import vocabulary_bp
from .flashcard import flashcard_bp
from .course import course_bp
from .practice import practice_bp
from .collab import collab_bp
from .quiz import quiz_learning_bp as quiz_bp

__all__ = [
    'vocabulary_bp',
    'flashcard_bp',
    'quiz_bp',
    'course_bp',
    'practice_bp',
    'collab_bp',
]
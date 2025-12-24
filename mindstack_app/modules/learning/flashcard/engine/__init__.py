# Flashcard Engine Module
# Pure sub-module containing core flashcard learning logic.
# This engine is designed to be called from multiple entry points:
# - vocabulary (single set learning)
# - practice (single/multi set practice)
# - collab (room-based learning)

from .algorithms import (
    get_new_only_items,
    get_due_items,
    get_hard_items,
    get_mixed_items,
    get_all_review_items,
    get_all_items_for_autoplay,
    get_accessible_flashcard_set_ids,
    get_pronunciation_items,
    get_writing_items,
    get_quiz_items,
    get_essay_items,
    get_listening_items,
    get_speaking_items,
    get_filtered_flashcard_sets,
    get_flashcard_mode_counts,
)

from .session_manager import FlashcardSessionManager
from .config import FlashcardLearningConfig
from .core import FlashcardEngine

__all__ = [
    # Algorithm functions
    'get_new_only_items',
    'get_due_items',
    'get_hard_items',
    'get_mixed_items',
    'get_all_review_items',
    'get_all_items_for_autoplay',
    'get_accessible_flashcard_set_ids',
    'get_pronunciation_items',
    'get_writing_items',
    'get_quiz_items',
    'get_essay_items',
    'get_listening_items',
    'get_speaking_items',
    'get_filtered_flashcard_sets',
    'get_flashcard_mode_counts',
    # Session management
    'FlashcardSessionManager',
    # Configuration
    'FlashcardLearningConfig',
    # Core Engine
    'FlashcardEngine',
]


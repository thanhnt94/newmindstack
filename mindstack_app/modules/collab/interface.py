# File: mindstack_app/modules/collab/interface.py
"""Public API (Gatekeeper) for the Collab module.

Other modules MUST import collab functionality through this interface.
This follows the Hexagonal Architecture pattern defined in MODULE_STRUCTURE.md.
"""

from .models import (
    # Flashcard Collab
    FlashcardCollabRoom,
    FlashcardCollabParticipant,
    FlashcardCollabMessage,
    FlashcardCollabRound,
    FlashcardCollabAnswer,
    FlashcardRoomProgress,
    # Quiz Battle
    QuizBattleRoom,
    QuizBattleParticipant,
    QuizBattleRound,
    QuizBattleAnswer,
    QuizBattleMessage,
)

__all__ = [
    # Flashcard Collab Models
    'FlashcardCollabRoom',
    'FlashcardCollabParticipant', 
    'FlashcardCollabMessage',
    'FlashcardCollabRound',
    'FlashcardCollabAnswer',
    'FlashcardRoomProgress',
    # Quiz Battle Models
    'QuizBattleRoom',
    'QuizBattleParticipant',
    'QuizBattleRound',
    'QuizBattleAnswer',
    'QuizBattleMessage',
]

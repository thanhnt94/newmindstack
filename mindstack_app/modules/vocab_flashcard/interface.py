"""Public interface for the vocab_flashcard module."""

from .engine.algorithms import (
    get_accessible_flashcard_set_ids,
    get_flashcard_mode_counts
)

class FlashcardInterface:
    @staticmethod
    def get_user_stats(user_id: int):
        """Get flashcard learning statistics for a user."""
        from .engine.session_manager import FlashcardSessionManager
        return FlashcardSessionManager.get_user_stats(user_id)

    @staticmethod
    def has_active_session(user_id: int) -> bool:
        """Check if the user has an active flashcard session."""
        from mindstack_app.modules.session.interface import SessionInterface
        session = SessionInterface.get_active_session(user_id, learning_mode='flashcard')
        return session is not None

    @staticmethod
    def get_flashcard_mode_counts(user_id: int, set_id: any, context: str = 'vocab') -> dict:
        """Get counts for different flashcard modes."""
        from .engine.algorithms import get_flashcard_mode_counts
        return get_flashcard_mode_counts(user_id, set_id, context=context)

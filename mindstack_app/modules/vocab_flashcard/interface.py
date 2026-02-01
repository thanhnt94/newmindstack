# File: mindstack_app/modules/vocab_flashcard/interface.py
from typing import List, Dict, Any
from .engine.algorithms import get_flashcard_mode_counts

class FlashcardInterface:
    @staticmethod
    def get_mode_counts(user_id: int, set_id: int) -> List[Dict[str, Any]]:
        """
        Public API to get available modes and their item counts for a set.
        Delegates to engine logic.
        """
        return get_flashcard_mode_counts(user_id, set_id)

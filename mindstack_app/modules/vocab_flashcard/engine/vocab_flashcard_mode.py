# mindstack_app/modules/vocab_flashcard/engine/vocab_flashcard_mode.py
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class FlashcardMode:
    id: str
    label: str
    icon: str
    color: str
    filter_method: str  # Name of the method in FlashcardQueryBuilder
    description: Optional[str] = None

class FlashcardModeRegistry:
    """
    Registry for flashcard modes, organized by context (e.g., 'vocab', 'collab').
    """
    _registry: Dict[str, List[FlashcardMode]] = {}

    @classmethod
    def register_modes(cls, context: str, modes: List[FlashcardMode]):
        """Register a list of modes for a specific context."""
        # Override existing modes for the context to ensure clean state
        cls._registry[context] = modes

    @classmethod
    def get_modes(cls, context: str) -> List[FlashcardMode]:
        """Get all modes registered for a context."""
        return cls._registry.get(context, [])

    @classmethod
    def get_mode_by_id(cls, mode_id: str, context: Optional[str] = None) -> Optional[FlashcardMode]:
        """
        Find a mode by its ID. 
        If context is provided, searches only within that context.
        Otherwise, searches all contexts.
        """
        if context:
            for mode in cls.get_modes(context):
                if mode.id == mode_id:
                    return mode
        else:
            for context_modes in cls._registry.values():
                for mode in context_modes:
                    if mode.id == mode_id:
                        return mode
        return None

# Helper functions for easier access
def register_flashcard_modes(context: str, modes: List[FlashcardMode]):
    FlashcardModeRegistry.register_modes(context, modes)

def get_flashcard_modes(context: str) -> List[FlashcardMode]:
    return FlashcardModeRegistry.get_modes(context)

def get_flashcard_mode_by_id(mode_id: str, context: Optional[str] = None) -> Optional[FlashcardMode]:
    return FlashcardModeRegistry.get_mode_by_id(mode_id, context)

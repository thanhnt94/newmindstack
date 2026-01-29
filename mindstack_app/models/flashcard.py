"""Flashcard set and item models."""
from __future__ import annotations
from .learning import LearningContainer, LearningItem

class FlashcardSet(LearningContainer):
    """Specialized LearningContainer for Flashcard Sets."""
    __mapper_args__ = {
        'polymorphic_identity': 'FLASHCARD_SET'
    }

    def __repr__(self):
        return f"<FlashcardSet {self.container_id}: {self.title}>"

class Flashcard(LearningItem):
    """Specialized LearningItem for Flashcards."""
    __mapper_args__ = {
        'polymorphic_identity': 'FLASHCARD'
    }

    def __repr__(self):
        return f"<Flashcard {self.item_id}>"

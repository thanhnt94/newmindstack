# File: mindstack_app/modules/vocab_flashcard/services/query_builder.py
# FlashcardQueryBuilder - Helper for constructing SQLAlchemy queries for flashcards.

from sqlalchemy import func, or_, and_
from mindstack_app.models import LearningItem, LearningContainer, db
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface

class FlashcardQueryBuilder:
    """
    Builder pattern for constructing complex Flashcard item queries.
    Uses generic FSRS Interface for filtering.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        # Base query: Flashcard or Vocabulary Items
        self._query = LearningItem.query.filter(
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )
        self._joined_progress = False

    def filter_by_containers(self, container_ids):
        """Filter items by a list of container IDs."""
        if not container_ids:
            self._query = self._query.filter(func.false())
        else:
            self._query = self._query.filter(LearningItem.container_id.in_(container_ids))
        return self

    def filter_new_only(self):
        """Filter for NEW items."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'new')
        return self

    def filter_due_only(self):
        """Filter for DUE items."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'due')
        return self

    def filter_hard_only(self):
        """Filter for HARD items."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'hard')
        return self

    def filter_available(self):
        """Filter for items that should be studied (NEW or DUE)."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'available')
        return self

    def filter_mixed(self):
        """Smart mix of Due & New items."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'mixed')
        return self

    def filter_sequential(self):
        """Sequential order for available (due/new) items."""
        # Reuse 'available' filter but override ordering
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'available')
        # Re-apply ordering to ensure sequential (override FSRS default if any)
        self._query = self._query.order_by(LearningItem.order_in_container.asc())
        return self

    def filter_all_review(self):
        """Filter for all reviewed items."""
        self._query = FsrsInterface.apply_memory_filter(self._query, self.user_id, 'review')
        return self

    def exclude_items(self, item_ids):
        """Exclude specific item IDs."""
        if item_ids:
            self._query = self._query.filter(LearningItem.item_id.notin_(item_ids))
        return self

    def get_query(self):
        """Return the constructed SQLAlchemy query object."""
        return self._query

    def count(self):
        """Execute count on the current query."""
        return self._query.count()

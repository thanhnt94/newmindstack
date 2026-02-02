# File: flashcard/engine/services/query_builder.py
# FlashcardQueryBuilder - Helper for constructing SQLAlchemy queries for flashcards.

from sqlalchemy import func, or_, and_
from mindstack_app.models import LearningItem, LearningContainer, db
from mindstack_app.modules.fsrs.models import ItemMemoryState

class FlashcardQueryBuilder:
    """
    Builder pattern for constructing complex Flashcard item queries.
    Uses ItemMemoryState for FSRS logic.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        # Base query: Flashcard or Vocabulary Items
        self._query = LearningItem.query.filter(
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )
        self._joined_progress = False

    def _join_progress(self):
        """Internal: Join ItemMemoryState table if not already joined."""
        if not self._joined_progress:
            # Join condition: Item matches, User matches.
            self._query = self._query.outerjoin(
                ItemMemoryState,
                (ItemMemoryState.item_id == LearningItem.item_id) &
                (ItemMemoryState.user_id == self.user_id)
            )
            self._joined_progress = True

    def filter_by_containers(self, container_ids):
        """Filter items by a list of container IDs."""
        if not container_ids:
            self._query = self._query.filter(func.false())
        else:
            self._query = self._query.filter(LearningItem.container_id.in_(container_ids))
        return self

    def filter_new_only(self):
        """Filter for NEW items (State=0 or NULL)."""
        self._join_progress()
        self._query = self._query.filter(
            or_(
                ItemMemoryState.state_id.is_(None),
                ItemMemoryState.state == 0
            )
        )
        self._query = self._query.order_by(LearningItem.order_in_container.asc())
        return self

    def filter_due_only(self):
        """Filter for DUE items (State!=0 AND Due<=Now)."""
        from datetime import datetime, timezone
        self._join_progress()
        self._query = self._query.filter(
            ItemMemoryState.state != 0,
            ItemMemoryState.due_date <= datetime.now(timezone.utc)
        )
        self._query = self._query.order_by(ItemMemoryState.due_date.asc())
        return self

    def filter_hard_only(self):
        """Filter for HARD items (Difficulty >= 7.0)."""
        self._join_progress()
        self._query = self._query.filter(
            ItemMemoryState.difficulty >= 7.0
        )
        return self

    def filter_available(self):
        """Filter for items that should be studied (NEW or DUE)."""
        from datetime import datetime, timezone
        self._join_progress()
        now = datetime.now(timezone.utc)
        self._query = self._query.filter(
            or_(
                ItemMemoryState.state_id.is_(None), # Never seen
                ItemMemoryState.state == 0,         # Explicitly New
                and_(
                    ItemMemoryState.state != 0,     # Reviewed
                    ItemMemoryState.due_date <= now # But due (R <= desired_retention)
                )
            )
        )
        return self

    def filter_mixed(self):
        """Smart mix of Due & New items, excluding those not yet due."""
        self.filter_available()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        self._query = self._query.order_by(
            # Priority 1: Due items 
            (ItemMemoryState.due_date <= now).desc(),
            # Priority 2: New items
            ItemMemoryState.state == 0, 
            # Randomize
            func.random()
        )
        return self

    def filter_sequential(self):
        """Sequential order for available (due/new) items."""
        self.filter_available()
        self._query = self._query.order_by(LearningItem.order_in_container.asc())
        return self

    def filter_all_review(self):
        """Filter for all reviewed items (State!=0)."""
        self._join_progress()
        self._query = self._query.filter(
            ItemMemoryState.state != 0
        )
        self._query = self._query.order_by(func.random())
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

"""
FlashcardQueryBuilder - Fluent Query Builder for Flashcard Items

Provides a clean, chainable API for building SQLAlchemy queries
for flashcard items with common filters.
"""
from typing import Optional, Union, List, Set
from flask import current_app
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Query

from mindstack_app.models import (
    db,
    LearningItem,
    LearningContainer,
    UserContainerState,
)
from mindstack_app.modules.learning.models import LearningProgress
from .permission_service import FlashcardPermissionService


class FlashcardQueryBuilder:
    """
    Fluent builder for constructing flashcard item queries.
    
    Usage:
        items = (FlashcardQueryBuilder(user_id)
            .for_container(container_id)
            .exclude_archived()
            .only_due()
            .build()
            .limit(20)
            .all())
    """
    
    def __init__(self, user_id: int):
        """
        Initialize the query builder.
        
        Args:
            user_id: The user ID for permission and progress filtering
        """
        self.user_id = user_id
        self._query = LearningItem.query.filter(
            LearningItem.item_type == 'FLASHCARD'
        )
        self._progress_joined = False
        self._archive_joined = False
        self._container_ids: Set[int] = set()
    
    def for_container(self, container_id: Union[int, str, List]) -> 'FlashcardQueryBuilder':
        """
        Filter by container(s) with permission checking.
        
        Args:
            container_id: Container ID, 'all', or list of IDs
            
        Returns:
            Self for chaining
        """
        self._container_ids = FlashcardPermissionService.normalize_container_id(
            self.user_id, container_id
        )
        
        if not self._container_ids:
            # No accessible containers - return empty query
            self._query = self._query.filter(False)
        else:
            self._query = self._query.filter(
                LearningItem.container_id.in_(self._container_ids)
            )
        
        return self
    
    def exclude_archived(self) -> 'FlashcardQueryBuilder':
        """
        Exclude items from archived containers.
        
        Returns:
            Self for chaining
        """
        if not self._archive_joined:
            self._query = self._query.outerjoin(
                UserContainerState,
                and_(
                    UserContainerState.container_id == LearningItem.container_id,
                    UserContainerState.user_id == self.user_id
                )
            ).filter(
                or_(
                    UserContainerState.is_archived == False,
                    UserContainerState.is_archived == None
                )
            )
            self._archive_joined = True
        
        return self
    
    def _join_progress(self, outer: bool = False) -> 'FlashcardQueryBuilder':
        """Internal: Join LearningProgress table if not already joined."""
        if not self._progress_joined:
            join_condition = and_(
                LearningProgress.item_id == LearningItem.item_id,
                LearningProgress.user_id == self.user_id,
                LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
            )
            
            if outer:
                self._query = self._query.outerjoin(LearningProgress, join_condition)
            else:
                self._query = self._query.join(LearningProgress, join_condition)
            
            self._progress_joined = True
        
        return self
    
    def only_new(self) -> 'FlashcardQueryBuilder':
        """
        Filter to only new items (no progress or STATE_NEW).
        
        Returns:
            Self for chaining
        """
        self._join_progress(outer=True)
        self._query = self._query.filter(
            or_(
                LearningProgress.item_id == None,
                LearningProgress.fsrs_state == LearningProgress.STATE_NEW
            )
        )
        return self
    
    def only_due(self) -> 'FlashcardQueryBuilder':
        """
        Filter to only due items (fsrs_due <= now).
        
        Returns:
            Self for chaining
        """
        self._join_progress(outer=False)
        self._query = self._query.filter(
            LearningProgress.fsrs_due <= func.now()
        )
        return self
    
    def only_due_or_new(self) -> 'FlashcardQueryBuilder':
        """
        Filter to only due or new items.
        
        Returns:
            Self for chaining
        """
        self._join_progress(outer=True)
        self._query = self._query.filter(
            or_(
                LearningProgress.item_id == None,
                LearningProgress.fsrs_state == LearningProgress.STATE_NEW,
                LearningProgress.fsrs_due <= func.now()
            )
        )
        return self
    
    def only_reviewed(self) -> 'FlashcardQueryBuilder':
        """
        Filter to items with learning progress (not NEW state).
        
        Returns:
            Self for chaining
        """
        self._join_progress(outer=False)
        self._query = self._query.filter(
            LearningProgress.fsrs_state != LearningProgress.STATE_NEW
        )
        return self
    
    def order_by_due(self, ascending: bool = True) -> 'FlashcardQueryBuilder':
        """
        Order by due date.
        
        Args:
            ascending: True for oldest first, False for newest first
            
        Returns:
            Self for chaining
        """
        self._join_progress(outer=True)
        if ascending:
            self._query = self._query.order_by(LearningProgress.fsrs_due.asc())
        else:
            self._query = self._query.order_by(LearningProgress.fsrs_due.desc())
        return self
    
    def order_random(self) -> 'FlashcardQueryBuilder':
        """
        Order randomly.
        
        Returns:
            Self for chaining
        """
        self._query = self._query.order_by(func.random())
        return self
    
    def order_by_container_order(self) -> 'FlashcardQueryBuilder':
        """
        Order by order_in_container field.
        
        Returns:
            Self for chaining
        """
        self._query = self._query.order_by(
            LearningItem.order_in_container.asc(),
            LearningItem.item_id.asc()
        )
        return self
    
    def build(self) -> Query:
        """
        Return the built query without executing.
        
        Returns:
            SQLAlchemy Query object
        """
        return self._query
    
    def count(self) -> int:
        """
        Execute query and return count.
        
        Returns:
            Number of matching items
        """
        return self._query.count()
    
    def execute(self, limit: Optional[int] = None) -> List[LearningItem]:
        """
        Execute query with optional limit.
        
        Args:
            limit: Maximum number of items to return (None = all)
            
        Returns:
            List of LearningItem objects
        """
        if limit is not None and limit != 999999:
            return self._query.limit(limit).all()
        return self._query.all()

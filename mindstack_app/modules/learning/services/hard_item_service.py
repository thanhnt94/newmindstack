"""
Hard Item Service
=================

Centralized service for identifying "hard" learning items.
Consolidates logic that was previously scattered across multiple modules.

A "hard" item is one that the user is struggling with, determined by:
1. Manual marker: User explicitly marked the item as 'difficult' (UserItemMarker)
2. Incorrect streak: User got it wrong >= HARD_ITEM_MIN_INCORRECT_STREAK times in a row
3. Stuck: User has reviewed many times (> HARD_ITEM_MAX_REPETITIONS) but stability is still low (< 7.0 days)
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import or_, and_

from mindstack_app.models import db, LearningItem
from mindstack_app.models.learning_progress import LearningProgress
from mindstack_app.models.user import UserItemMarker
from mindstack_app.services.memory_power_config_service import MemoryPowerConfigService

if TYPE_CHECKING:
    from sqlalchemy.orm import Query


class HardItemService:
    """Centralized service for hard item detection."""

    # === Config Getters ===
    
    @staticmethod
    def _get_min_streak() -> int:
        """Get minimum incorrect streak to be considered hard."""
        return MemoryPowerConfigService.get('HARD_ITEM_MIN_INCORRECT_STREAK', 3)
    
    @staticmethod
    def _get_max_reps() -> int:
        """Get max repetitions threshold for 'stuck' detection."""
        return MemoryPowerConfigService.get('HARD_ITEM_MAX_REPETITIONS', 10)
    
    @staticmethod
    def _get_stuck_stability() -> float:
        """Get stability threshold (days) for 'stuck' detection.
        Fixed at 7 days for now.
        """
        return 7.0

    # === Core Methods ===

    @classmethod
    def is_hard_item(
        cls,
        user_id: int,
        item_id: int,
        learning_mode: str = LearningProgress.MODE_FLASHCARD
    ) -> bool:
        """
        Check if a specific item is considered 'hard' for a user.
        
        Args:
            user_id: The user's ID
            item_id: The learning item ID
            learning_mode: The learning mode (flashcard, quiz, etc.)
            
        Returns:
            True if the item is considered hard
        """
        # Check manual marker first
        manual_marker = UserItemMarker.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            marker_type='difficult'
        ).first()
        
        if manual_marker:
            return True
        
        # Check learning progress
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=learning_mode
        ).first()
        
        if not progress:
            return False
        
        min_streak = cls._get_min_streak()
        max_reps = cls._get_max_reps()
        stuck_stability = cls._get_stuck_stability()
        
        # Criterion 2: Incorrect streak
        if (progress.incorrect_streak or 0) >= min_streak:
            return True
        
        # Criterion 3: Stuck (high reps, low stability)
        if (progress.repetitions or 0) > max_reps and (progress.fsrs_stability or 0) < stuck_stability:
            return True
        
        return False

    @classmethod
    def get_hard_item_ids(
        cls,
        user_id: int,
        container_id: Optional[int] = None,
        learning_mode: str = LearningProgress.MODE_FLASHCARD
    ) -> List[int]:
        """
        Get list of hard item IDs for a user.
        
        Args:
            user_id: The user's ID
            container_id: Optional container to filter by
            learning_mode: The learning mode
            
        Returns:
            List of item IDs that are considered hard
        """
        query = cls.get_hard_items_query(user_id, container_id, learning_mode)
        return [item.item_id for item in query.all()]

    @classmethod
    def get_hard_items_query(
        cls,
        user_id: int,
        container_id: Optional[int] = None,
        learning_mode: str = LearningProgress.MODE_FLASHCARD
    ) -> "Query":
        """
        Get SQLAlchemy query for hard items.
        Useful for session managers that need to further filter/paginate.
        
        Args:
            user_id: The user's ID
            container_id: Optional container to filter by (can be 'all' for all containers)
            learning_mode: The learning mode
            
        Returns:
            SQLAlchemy Query object
        """
        min_streak = cls._get_min_streak()
        max_reps = cls._get_max_reps()
        stuck_stability = cls._get_stuck_stability()
        
        # Base query for items
        base_query = LearningItem.query
        
        if container_id and container_id != 'all':
            base_query = base_query.filter(LearningItem.container_id == container_id)
        
        # Subquery for manually marked items
        manual_marker_subquery = db.session.query(UserItemMarker.item_id).filter(
            UserItemMarker.user_id == user_id,
            UserItemMarker.marker_type == 'difficult'
        )
        
        # Join with LearningProgress and filter
        query = base_query.outerjoin(
            LearningProgress,
            and_(
                LearningProgress.item_id == LearningItem.item_id,
                LearningProgress.user_id == user_id,
                LearningProgress.learning_mode == learning_mode
            )
        ).filter(
            or_(
                # Criterion 1: Manual marker
                LearningItem.item_id.in_(manual_marker_subquery),
                # Criterion 2: Incorrect streak
                LearningProgress.incorrect_streak >= min_streak,
                # Criterion 3: Stuck (high reps, low stability)
                and_(
                    LearningProgress.repetitions > max_reps,
                    LearningProgress.fsrs_stability < stuck_stability
                )
            )
        )
        
        return query

    @classmethod
    def get_hard_count(
        cls,
        user_id: int,
        container_id: Optional[int] = None,
        learning_mode: str = LearningProgress.MODE_FLASHCARD
    ) -> int:
        """
        Get count of hard items.
        
        Args:
            user_id: The user's ID
            container_id: Optional container to filter by
            learning_mode: The learning mode
            
        Returns:
            Number of hard items
        """
        return cls.get_hard_items_query(user_id, container_id, learning_mode).count()

# File: mindstack_app/modules/fsrs/services/hard_item_service.py
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import or_, and_
from mindstack_app.models import db, LearningItem, UserItemMarker
from mindstack_app.modules.fsrs.models import ItemMemoryState
from .settings_service import FSRSSettingsService

class FSRSHardItemService:
    """Centralized service for hard item detection using FSRS metrics."""

    @staticmethod
    def _get_min_streak() -> int:
        return FSRSSettingsService.get('HARD_ITEM_MIN_INCORRECT_STREAK', 3)
    
    @staticmethod
    def _get_max_reps() -> int:
        return FSRSSettingsService.get('HARD_ITEM_MAX_REPETITIONS', 10)
    
    @staticmethod
    def _get_stuck_stability() -> float:
        return 7.0

    @classmethod
    def is_hard_item(cls, user_id: int, item_id: int, learning_mode: str = 'flashcard') -> bool:
        manual_marker = UserItemMarker.query.filter_by(
            user_id=user_id, item_id=item_id, marker_type='difficult'
        ).first()
        if manual_marker: return True
        
        # MIGRATED: Use ItemMemoryState
        state = ItemMemoryState.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        if not state: return False
        
        if (state.incorrect_streak or 0) >= cls._get_min_streak(): return True
        if (state.repetitions or 0) > cls._get_max_reps() and (state.stability or 0) < cls._get_stuck_stability():
            return True
        return False

    @classmethod
    def get_hard_items_query(cls, user_id: int, container_id: Optional[int] = None, learning_mode: str = 'flashcard'):
        min_streak = cls._get_min_streak()
        max_reps = cls._get_max_reps()
        stuck_stability = cls._get_stuck_stability()
        
        base_query = LearningItem.query
        if container_id and container_id != 'all':
            base_query = base_query.filter(LearningItem.container_id == container_id)
        
        manual_marker_subquery = db.session.query(UserItemMarker.item_id).filter(
            UserItemMarker.user_id == user_id, UserItemMarker.marker_type == 'difficult'
        )
        
        # MIGRATED: Use ItemMemoryState
        query = base_query.outerjoin(
            ItemMemoryState,
            and_(
                ItemMemoryState.item_id == LearningItem.item_id,
                ItemMemoryState.user_id == user_id
            )
        ).filter(
            or_(
                LearningItem.item_id.in_(manual_marker_subquery),
                ItemMemoryState.incorrect_streak >= min_streak,
                and_(
                    ItemMemoryState.repetitions > max_reps,
                    ItemMemoryState.stability < stuck_stability
                )
            )
        )
        return query

    @classmethod
    def get_hard_count(cls, user_id: int, container_id: Optional[int] = None, learning_mode: str = 'flashcard') -> int:
        """Return the count of hard items."""
        return cls.get_hard_items_query(user_id, container_id, learning_mode).count()
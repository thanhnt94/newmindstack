"""
Unified Progress Service
========================

Provides a single interface for all learning progress operations,
migrated to use ItemMemoryState (FSRS).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.sql import func

from mindstack_app.models import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from ..schemas import LearningProgressSchema

class ProgressService:
    """Unified service for all learning progress operations."""
    
    # === Core CRUD Operations ===
    
    @classmethod
    def get_or_create(
        cls,
        user_id: int,
        item_id: int,
        mode: str # mode is now context/ignored for retrieval
    ) -> tuple[ItemMemoryState, bool]:
        """Get existing memory state or create new record."""
        state = ItemMemoryState.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).first()
        
        if state:
            return state, False
        
        state = ItemMemoryState(
            user_id=user_id,
            item_id=item_id,
            state=0, # NEW
            created_at=func.now()
        )
        db.session.add(state)
        # Flush to get ID if needed
        db.session.flush()
        return state, True
    
    @classmethod
    def get_progress(
        cls,
        user_id: int,
        item_id: int,
        mode: str
    ) -> Optional[LearningProgressSchema]:
        """Get progress record if exists."""
        state = ItemMemoryState.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).first()
        if not state:
            return None
            
        # Map ItemMemoryState to LearningProgressSchema for compatibility
        return cls._map_to_schema(state, mode)
    
    @classmethod
    def _map_to_schema(cls, state: ItemMemoryState, mode: str) -> LearningProgressSchema:
        # Compatibility mapper
        return LearningProgressSchema(
            progress_id=state.state_id,
            user_id=state.user_id,
            item_id=state.item_id,
            learning_mode=mode, # Fake mode
            fsrs_state=state.state or 0,
            fsrs_stability=state.stability or 0.0,
            fsrs_difficulty=state.difficulty or 0.0,
            fsrs_due=state.due_date,
            fsrs_last_review=state.last_review,
            first_seen=state.created_at,
            lapses=state.lapses or 0,
            repetitions=state.repetitions or 0,
            times_correct=0, # Dropped
            times_incorrect=0, # Dropped
            correct_streak=state.streak or 0,
            mode_data=state.data
        )

    @classmethod
    def get_all_progress_for_user(
        cls,
        user_id: int,
        mode: Optional[str] = None,
        container_id: Optional[int] = None
    ) -> List[LearningProgressSchema]:
        """Get all progress records for a user."""
        query = ItemMemoryState.query.filter_by(user_id=user_id)
        
        if container_id:
            from mindstack_app.models import LearningItem
            query = query.join(LearningItem).filter(
                LearningItem.container_id == container_id
            )
        
        results = query.all()
        return [cls._map_to_schema(s, mode or 'unknown') for s in results]
    
    # === SRS Operations ===
    
    @classmethod
    def get_due_items(
        cls,
        user_id: int,
        mode: str,
        container_id: Optional[int] = None,
        limit: int = 100
    ) -> List[LearningProgressSchema]:
        """Get items due for review."""
        now = datetime.now(timezone.utc)
        
        query = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        )
        
        if container_id:
            from mindstack_app.models import LearningItem
            query = query.join(LearningItem).filter(
                LearningItem.container_id == container_id
            )
        
        results = query.order_by(ItemMemoryState.due_date).limit(limit).all()
        return [cls._map_to_schema(s, mode) for s in results]
    
    @classmethod
    def get_new_items(
        cls,
        user_id: int,
        mode: str,
        container_id: int,
        limit: int = 20
    ) -> List[int]:
        """Get item IDs that user hasn't studied yet."""
        from mindstack_app.models import LearningItem
        
        # Get items user already has state for
        studied_items = db.session.query(ItemMemoryState.item_id).filter(
            ItemMemoryState.user_id == user_id
        ).subquery()
        
        # Get items from container not yet studied
        new_items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            ~LearningItem.item_id.in_(studied_items)
        ).order_by(LearningItem.order_in_container).limit(limit).all()
        
        return [item.item_id for item in new_items]
    
    # === Statistics ===
    
    @classmethod
    def get_container_stats(
        cls,
        user_id: int,
        container_id: int,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get learning statistics for a container."""
        from mindstack_app.models import LearningItem
        
        total_items = LearningItem.query.filter_by(
            container_id=container_id
        ).count()
        
        # Progress query
        query = db.session.query(ItemMemoryState).join(LearningItem).filter(
            ItemMemoryState.user_id == user_id,
            LearningItem.container_id == container_id
        )
        
        progress_records = query.all()
        
        studied = len(progress_records)
        # Mastered: stability >= 21
        mastered = sum(1 for p in progress_records if (p.stability or 0) >= 21.0)
        # Learning: state 1 or 3
        learning = sum(1 for p in progress_records if p.state in (1, 3))
        
        total_correct = 0 # Not tracking aggregate correct/incorrect in ItemMemoryState
        total_incorrect = 0
        
        from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
        avg_retrievability = (
            sum(FsrsService.get_retrievability(p) for p in progress_records) / studied
            if studied > 0 else 0
        )
        
        return {
            'total_items': total_items,
            'studied': studied,
            'new': total_items - studied,
            'mastered': mastered,
            'learning': learning,
            'total_correct': total_correct,
            'total_incorrect': total_incorrect,
            'accuracy': 0, # Cannot calc from ItemMemoryState
            'avg_retrievability': avg_retrievability,
            'avg_mastery': avg_retrievability,
            'completion_percentage': (studied / total_items * 100) if total_items > 0 else 0,
        }
    
    # === Mode-Specific Methods (Delegates to FSRS Interface) ===
    
    @classmethod
    def update_flashcard_progress(
        cls,
        user_id: int,
        item_id: int,
        quality: int,
        **srs_updates
    ) -> LearningProgressSchema:
        """Update flashcard progress."""
        from mindstack_app.modules.fsrs.interface import FSRSInterface
        # This seems to duplicate logic if FSRSInterface.process_review was used.
        # But if this is called manually, we should use FSRSInterface.
        # However, FSRSInterface.process_review handles the logic.
        # Let's assume this method is legacy or used by simple updates.
        
        state, result = FSRSInterface.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode='flashcard'
        )
        db.session.commit()
        return cls._map_to_schema(state, 'flashcard')
    
    @classmethod
    def update_quiz_progress(
        cls,
        user_id: int,
        item_id: int,
        is_correct: bool
    ) -> LearningProgressSchema:
        """Update quiz progress."""
        from mindstack_app.modules.fsrs.interface import FSRSInterface
        quality = 3 if is_correct else 1
        
        state, result = FSRSInterface.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode='quiz'
        )
        db.session.commit()
        return cls._map_to_schema(state, 'quiz')
    
    @classmethod
    def update_memrise_progress(
        cls,
        user_id: int,
        item_id: int,
        is_correct: bool,
        duration_ms: int = 0
    ) -> LearningProgressSchema:
        from mindstack_app.modules.fsrs.interface import FSRSInterface
        quality = 3 if is_correct else 1
        state, result = FSRSInterface.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode='memrise',
            duration_ms=duration_ms
        )
        db.session.commit()
        return cls._map_to_schema(state, 'memrise')
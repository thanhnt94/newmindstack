"""
Unified Progress Service
========================

Provides a single interface for all learning progress operations,
working with the unified LearningProgress model.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.sql import func

from mindstack_app.models import db
from mindstack_app.models.learning_progress import LearningProgress


class ProgressService:
    """Unified service for all learning progress operations.
    
    This service abstracts the details of progress tracking across
    different learning modes (flashcard, quiz, memrise, etc.).
    """
    
    # === Core CRUD Operations ===
    
    @classmethod
    def get_or_create(
        cls,
        user_id: int,
        item_id: int,
        mode: str
    ) -> tuple[LearningProgress, bool]:
        """Get existing progress or create new record.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            mode: Learning mode ('flashcard', 'quiz', 'memrise', etc.)
            
        Returns:
            Tuple of (progress_record, is_new)
        """
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=mode
        ).first()
        
        if progress:
            return progress, False
        
        progress = LearningProgress(
            user_id=user_id,
            item_id=item_id,
            learning_mode=mode,
            status='new',
            first_seen=func.now()
        )
        db.session.add(progress)
        return progress, True
    
    @classmethod
    def get_progress(
        cls,
        user_id: int,
        item_id: int,
        mode: str
    ) -> Optional[LearningProgress]:
        """Get progress record if exists.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            mode: Learning mode
            
        Returns:
            LearningProgress or None
        """
        return LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=mode
        ).first()
    
    @classmethod
    def get_all_progress_for_user(
        cls,
        user_id: int,
        mode: Optional[str] = None,
        container_id: Optional[int] = None
    ) -> List[LearningProgress]:
        """Get all progress records for a user.
        
        Args:
            user_id: User ID
            mode: Optional filter by learning mode
            container_id: Optional filter by container
            
        Returns:
            List of LearningProgress records
        """
        query = LearningProgress.query.filter_by(user_id=user_id)
        
        if mode:
            query = query.filter_by(learning_mode=mode)
        
        if container_id:
            from mindstack_app.models import LearningItem
            query = query.join(LearningItem).filter(
                LearningItem.container_id == container_id
            )
        
        return query.all()
    
    # === SRS Operations ===
    
    @classmethod
    def get_due_items(
        cls,
        user_id: int,
        mode: str,
        container_id: Optional[int] = None,
        limit: int = 100
    ) -> List[LearningProgress]:
        """Get items due for review.
        
        Args:
            user_id: User ID
            mode: Learning mode
            container_id: Optional container filter
            limit: Maximum number of items
            
        Returns:
            List of due LearningProgress records
        """
        now = datetime.now(timezone.utc)
        
        query = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == mode,
            LearningProgress.due_time <= now
        )
        
        if container_id:
            from mindstack_app.models import LearningItem
            query = query.join(LearningItem).filter(
                LearningItem.container_id == container_id
            )
        
        return query.order_by(LearningProgress.due_time).limit(limit).all()
    
    @classmethod
    def get_new_items(
        cls,
        user_id: int,
        mode: str,
        container_id: int,
        limit: int = 20
    ) -> List[int]:
        """Get item IDs that user hasn't studied yet in this mode.
        
        Args:
            user_id: User ID
            mode: Learning mode  
            container_id: Container ID
            limit: Maximum number of items
            
        Returns:
            List of item IDs
        """
        from mindstack_app.models import LearningItem
        
        # Get items user already has progress for
        studied_items = db.session.query(LearningProgress.item_id).filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == mode
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
        """Get learning statistics for a container.
        
        Args:
            user_id: User ID
            container_id: Container ID
            mode: Optional learning mode filter
            
        Returns:
            Dictionary with stats
        """
        from mindstack_app.models import LearningItem
        
        # Total items in container
        total_items = LearningItem.query.filter_by(
            container_id=container_id
        ).count()
        
        # Progress query
        query = db.session.query(LearningProgress).join(LearningItem).filter(
            LearningProgress.user_id == user_id,
            LearningItem.container_id == container_id
        )
        
        if mode:
            query = query.filter(LearningProgress.learning_mode == mode)
        
        progress_records = query.all()
        
        studied = len(progress_records)
        mastered = sum(1 for p in progress_records if p.status == 'mastered')
        learning = sum(1 for p in progress_records if p.status in ('learning', 'reviewing'))
        
        total_correct = sum(p.times_correct or 0 for p in progress_records)
        total_incorrect = sum(p.times_incorrect or 0 for p in progress_records)
        
        avg_mastery = (
            sum(p.mastery or 0 for p in progress_records) / studied
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
            'accuracy': total_correct / (total_correct + total_incorrect) if (total_correct + total_incorrect) > 0 else 0,
            'avg_mastery': avg_mastery,
            'completion_percentage': (studied / total_items * 100) if total_items > 0 else 0,
        }
    
    # === Mode-Specific Convenience Methods ===
    
    @classmethod
    def update_flashcard_progress(
        cls,
        user_id: int,
        item_id: int,
        quality: int,
        **srs_updates
    ) -> LearningProgress:
        """Update flashcard progress with SRS algorithm results.
        
        Args:
            user_id: User ID
            item_id: Item ID
            quality: Answer quality (0-5)
            **srs_updates: SRS-calculated values (interval, ef, repetitions, etc.)
            
        Returns:
            Updated LearningProgress
        """
        progress, is_new = cls.get_or_create(user_id, item_id, 'flashcard')
        
        progress.last_reviewed = datetime.now(timezone.utc)
        
        # Update statistics based on quality
        if quality >= 4:  # Correct
            progress.times_correct = (progress.times_correct or 0) + 1
            progress.correct_streak = (progress.correct_streak or 0) + 1
            progress.incorrect_streak = 0
            progress.vague_streak = 0
        elif quality >= 2:  # Vague
            progress.times_vague = (progress.times_vague or 0) + 1
            progress.vague_streak = (progress.vague_streak or 0) + 1
            progress.correct_streak = 0
            progress.incorrect_streak = 0
        else:  # Incorrect
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
            progress.incorrect_streak = (progress.incorrect_streak or 0) + 1
            progress.correct_streak = 0
            progress.vague_streak = 0
        
        # Apply SRS updates
        for key, value in srs_updates.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        
        return progress
    
    @classmethod
    def update_quiz_progress(
        cls,
        user_id: int,
        item_id: int,
        is_correct: bool
    ) -> LearningProgress:
        """Update quiz progress after an answer.
        
        Args:
            user_id: User ID
            item_id: Item ID
            is_correct: Whether answer was correct
            
        Returns:
            Updated LearningProgress
        """
        progress, is_new = cls.get_or_create(user_id, item_id, 'quiz')
        
        progress.last_reviewed = datetime.now(timezone.utc)
        
        if is_correct:
            progress.times_correct = (progress.times_correct or 0) + 1
            progress.correct_streak = (progress.correct_streak or 0) + 1
            progress.incorrect_streak = 0
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
            progress.incorrect_streak = (progress.incorrect_streak or 0) + 1
            progress.correct_streak = 0
        
        # Update status based on performance
        total = (progress.times_correct or 0) + (progress.times_incorrect or 0)
        ratio = (progress.times_correct or 0) / total if total > 0 else 0
        
        if total > 10 and ratio > 0.8:
            progress.status = 'mastered'
        elif total > 5 and ratio < 0.5:
            # [UPDATED] Do NOT set status='hard' rigidly.
            progress.status = 'learning'
        elif is_new:
            progress.status = 'learning'
        
        # Update mastery
        progress.mastery = min(1.0, ratio)
        
        return progress
    
    @classmethod
    def update_memrise_progress(
        cls,
        user_id: int,
        item_id: int,
        is_correct: bool,
        memory_intervals: Dict[int, int]
    ) -> LearningProgress:
        """Update Memrise-style progress.
        
        Args:
            user_id: User ID
            item_id: Item ID
            is_correct: Whether answer was correct
            memory_intervals: Dict mapping memory_level -> interval_minutes
            
        Returns:
            Updated LearningProgress
        """
        progress, is_new = cls.get_or_create(user_id, item_id, 'memrise')
        
        progress.last_reviewed = datetime.now(timezone.utc)
        
        current_level = progress.memory_level
        
        if is_correct:
            progress.times_correct = (progress.times_correct or 0) + 1
            progress.current_streak = progress.current_streak + 1
            progress.session_reps = progress.session_reps + 1
            
            # Level up
            new_level = min(7, current_level + 1)
            progress.memory_level = new_level
            
            # Calculate next due time
            interval_minutes = memory_intervals.get(new_level, 10)
            progress.interval = interval_minutes
            progress.due_time = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
            
            # Update status
            if new_level >= 7:
                progress.status = 'mastered'
            elif new_level >= 4:
                progress.status = 'reviewing'
            else:
                progress.status = 'learning'
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
            progress.current_streak = 0
            progress.session_reps = progress.session_reps + 1
            
            # Reset to level 1 (or stay at 0)
            new_level = max(1, current_level - 2)  # Drop 2 levels on mistake
            progress.memory_level = new_level
            
            # Short relearning interval
            relearning_interval = memory_intervals.get(0, 10)
            progress.interval = relearning_interval
            progress.due_time = datetime.now(timezone.utc) + timedelta(minutes=relearning_interval)
            progress.status = 'learning'
        
        # Update mastery
        progress.mastery = progress.memory_level / 7.0
        
        return progress

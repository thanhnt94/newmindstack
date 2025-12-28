"""
SRS Service - Database Layer for Spaced Repetition System

Handles database persistence for SRS operations.
Delegates all calculations to SrsEngine (pure logic).

This service:
- Fetches/creates LearningProgress records
- Delegates calculations to engines
- Saves results to database (LearningProgress, ReviewLog)
- Returns updated progress
"""

import datetime
from typing import Optional
from mindstack_app.models import db, LearningItem, ReviewLog
from mindstack_app.models.learning_progress import LearningProgress

from ..logics.srs_engine import SrsEngine, SrsConstants
from ..logics.memory_engine import MemoryEngine, ProgressState
from ..logics.scoring_engine import ScoringEngine


class SrsService:
    """
    Service layer for SRS operations.
    Coordinates between database and calculation engines.
    """

    # === Unified Update Method ===

    @staticmethod
    def update(
        user_id: int,
        item_id: int,
        quality: int,
        source_mode: str = 'flashcard',
        use_memory_power: bool = True,
        duration_ms: int = 0,
        user_answer: str = None
    ) -> LearningProgress:
        """
        Unified SRS update method.
        Routes to appropriate algorithm based on flag.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (0-5)
            source_mode: Learning mode ('flashcard', 'quiz', etc.)
            use_memory_power: If True, use Memory Power system; else SM-2
            duration_ms: Time taken to answer (milliseconds)
            user_answer: User's submitted answer
        
        Returns:
            Updated LearningProgress instance
        """
        if use_memory_power:
            return SrsService._update_memory_power(
                user_id, item_id, quality, source_mode, duration_ms, user_answer
            )
        else:
            return SrsService._update_sm2(
                user_id, item_id, quality, source_mode, duration_ms, user_answer
            )

    # === SM-2 Algorithm Implementation ===

    @staticmethod
    def _update_sm2(
        user_id: int,
        item_id: int,
        quality: int,
        source_mode: str = 'flashcard',
        duration_ms: int = 0,
        user_answer: str = None
    ) -> LearningProgress:
        """
        Update progress using SM-2 algorithm.
        Delegates calculations to SrsEngine.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (0-5)
            source_mode: Learning mode
            duration_ms: Duration in milliseconds
            user_answer: User's answer
        
        Returns:
            Updated LearningProgress instance
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Fetch or create progress record
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode=source_mode
        ).first()
        
        if not progress:
            progress = LearningProgress(
                user_id=user_id, item_id=item_id,
                learning_mode=source_mode,
                status='new',
                easiness_factor=SrsConstants.DEFAULT_EASINESS_FACTOR,
                repetitions=0,
                interval=0,
                first_seen=now
            )
            db.session.add(progress)
        
        # Ensure timezone aware
        if progress.first_seen and progress.first_seen.tzinfo is None:
            progress.first_seen = progress.first_seen.replace(tzinfo=datetime.timezone.utc)

        # 2. Update legacy counters
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1

        # 3. Check early review
        due_time = progress.due_time
        if due_time and due_time.tzinfo is None:
            due_time = due_time.replace(tzinfo=datetime.timezone.utc)
        
        is_early_review = due_time and now < due_time

        # 4. Apply SRS update
        if is_early_review:
            # Only update last_reviewed, don't change SRS state
            progress.last_reviewed = now
        else:
            # Full SRS update
            if progress.status == 'new':
                progress.status = 'learning'
            
            # Delegate calculation to SrsEngine
            new_status, new_interval, new_ef, new_reps = SrsEngine.calculate_next_state(
                current_status=progress.status,
                current_interval=progress.interval or 0,
                current_ef=progress.easiness_factor or SrsConstants.DEFAULT_EASINESS_FACTOR,
                current_reps=progress.repetitions or 0,
                quality=quality
            )
            
            # Apply calculated state
            progress.status = new_status
            progress.repetitions = new_reps
            progress.easiness_factor = new_ef
            progress.interval = new_interval
            progress.last_reviewed = now
            progress.due_time = now + datetime.timedelta(minutes=new_interval)

            # Check graduation (learning → reviewing)
            if progress.status == 'learning' and SrsEngine.should_graduate(progress.repetitions, quality):
                progress.status = 'reviewing'
                progress.interval = SrsConstants.GRADUATING_INTERVAL_MINUTES
                progress.due_time = now + datetime.timedelta(minutes=progress.interval)
                progress.repetitions = 1
        
        # 5. Log to ReviewLog with score
        score_change = ScoringEngine.quality_to_score(quality)
        is_correct = SrsEngine.is_correct(quality)
        
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            interval=progress.interval,
            easiness_factor=progress.easiness_factor,
            review_type=source_mode,
            duration_ms=duration_ms,
            user_answer=user_answer,
            score_change=score_change,
            is_correct=is_correct
        )
        db.session.add(log_entry)

        return progress

    # === Memory Power System Implementation ===

    @staticmethod
    def _update_memory_power(
        user_id: int,
        item_id: int,
        quality: int,
        source_mode: str = 'flashcard',
        duration_ms: int = 0,
        user_answer: str = None
    ) -> LearningProgress:
        """
        Update progress using Memory Power system.
        Delegates calculations to MemoryEngine.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (0-5)
            source_mode: Learning mode
            duration_ms: Duration in milliseconds
            user_answer: User's answer
        
        Returns:
            Updated LearningProgress instance
        """
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode=source_mode
        ).first()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if not progress:
            progress = LearningProgress(
                user_id=user_id,
                item_id=item_id,
                learning_mode=source_mode,
                status='new',
                easiness_factor=SrsConstants.DEFAULT_EASINESS_FACTOR,
                repetitions=0,
                interval=0,
                mastery=0.0,
                correct_streak=0,
                incorrect_streak=0,
                first_seen=now
            )
            db.session.add(progress)
        
        # Build current state for MemoryEngine
        current_state = ProgressState(
            status=progress.status or 'new',
            mastery=progress.mastery or 0.0,
            repetitions=progress.repetitions or 0,
            interval=progress.interval or 0,
            correct_streak=progress.correct_streak or 0,
            incorrect_streak=progress.incorrect_streak or 0,
            easiness_factor=progress.easiness_factor or SrsConstants.DEFAULT_EASINESS_FACTOR
        )
        
        # Process answer through MemoryEngine
        result = MemoryEngine.process_answer(current_state, quality, now)
        new_state = result.new_state
        
        # Apply new state to progress
        progress.status = new_state.status
        progress.mastery = new_state.mastery
        progress.repetitions = new_state.repetitions
        progress.interval = new_state.interval
        progress.correct_streak = new_state.correct_streak
        progress.incorrect_streak = new_state.incorrect_streak
        progress.easiness_factor = new_state.easiness_factor
        progress.last_reviewed = now
        progress.due_time = now + datetime.timedelta(minutes=new_state.interval)
        
        # Update legacy counters
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
        
        # Log to ReviewLog with full state snapshots
        score_change = ScoringEngine.quality_to_score(quality)
        is_correct = SrsEngine.is_correct(quality)
        
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            interval=new_state.interval,
            easiness_factor=new_state.easiness_factor,
            review_type=source_mode,
            mastery_snapshot=new_state.mastery,
            memory_power_snapshot=result.memory_power,
            duration_ms=duration_ms,
            user_answer=user_answer,
            score_change=score_change,
            is_correct=is_correct
        )
        db.session.add(log_entry)
        
        return progress

    # === Compatibility Aliases (Deprecated) ===

    @staticmethod
    def update_item_progress(*args, **kwargs) -> LearningProgress:
        """Legacy method - use update() instead."""
        return SrsService._update_sm2(*args, **kwargs)

    @staticmethod
    def update_with_memory_power(*args, **kwargs) -> LearningProgress:
        """Legacy method - use update() with use_memory_power=True instead."""
        return SrsService._update_memory_power(*args, **kwargs)

    # === Helper Methods ===

    @staticmethod
    def get_memory_power(progress: LearningProgress) -> float:
        """
        Calculate current Memory Power for a progress record.
        
        Returns:
            Memory Power percentage (0.0 - 1.0)
        """
        if not progress:
            return 0.0
        
        mastery = progress.mastery or 0.0
        retention = MemoryEngine.calculate_retention(
            progress.last_reviewed,
            progress.interval or 0
        )
        
        return MemoryEngine.calculate_memory_power(mastery, retention)

    # === Learning Interaction Processing ===

    @staticmethod
    def process_interaction(user_id: int, item_id: int, mode: str, result_data: dict):
        """
        Process a user's learning interaction and update SRS progress.
        
        Handles quality normalization and delegates to update().

        Args:
            user_id: User ID
            item_id: Learning item ID
            mode: Learning mode ('flashcard', 'listening', 'mcq', etc.)
            result_data: Mode-specific result data (quality, accuracy, is_correct, etc.)

        Returns:
            dict: Summary (quality, status, next_review, score_change)
        """
        # 1. Normalize result to SRS quality using engine
        quality = SrsEngine.normalize_quality(mode, result_data)

        # 2. Update progress
        progress = SrsService.update(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            source_mode=mode,
            use_memory_power=True,  # Default to Memory Power system
            duration_ms=result_data.get('duration_ms', 0),
            user_answer=result_data.get('user_answer')
        )
        
        # 3. Get latest score from ReviewLog
        latest_log = ReviewLog.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).order_by(ReviewLog.timestamp.desc()).first()
        
        score_change = latest_log.score_change if latest_log else 0

        return {
            'quality': quality,
            'status': progress.status,
            'next_review': progress.due_time,
            'score_change': score_change
        }

    @staticmethod
    def calculate_retention_rate(last_reviewed: datetime.datetime, interval_minutes: int) -> int:
        """
        Calculate retention probability as percentage.
        Delegates to SrsEngine.
        
        Args:
            last_reviewed: When item was last reviewed
            interval_minutes: Scheduled interval in minutes
        
        Returns:
            Retention percentage (0-100)
        """
        return SrsEngine.calculate_retention_percentage(last_reviewed, interval_minutes)

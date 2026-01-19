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
from flask import current_app
from mindstack_app.models import db, LearningItem, ReviewLog, User
from mindstack_app.models.learning_progress import LearningProgress

from ..logics.srs_engine import SrsEngine, SrsConstants
from ..logics.memory_engine import MemoryEngine, ProgressState
from ..logics.scoring_engine import ScoringEngine
from ..logics.unified_srs import UnifiedSrsSystem, SrsResult


class SrsService:
    """
    Service layer for SRS operations.
    Coordinates between database and calculation engines.
    """

    # === NEW: Unified Update Method (Hybrid SM-2 + Memory Power) ===

    @staticmethod
    def update_unified(
        user_id: int,
        item_id: int,
        quality: int,
        mode: str = 'flashcard',
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None,
        duration_ms: int = 0,
        is_cram: bool = False,  # Cram mode support
        # Session context fields
        session_id: int = None,
        container_id: int = None,
        learning_mode: str = None,
        streak_position: int = 0
    ) -> tuple[LearningProgress, SrsResult]:
        """
        NEW: Update progress using UnifiedSrsSystem (Hybrid approach).
        
        This method combines SM-2 for scheduling with Memory Power for analytics.
        Recommended for all new code.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (0-5)
            mode: Learning mode ('flashcard', 'quiz_mcq', 'typing', etc.)
            is_first_time: Whether this is first time seeing item
            response_time_seconds: Time taken to answer
            duration_ms: Response time in milliseconds (for stats)
            is_cram: If True, only update stats/history, NOT schedule (unless new)
            session_id: Learning session ID for context
            container_id: Container ID for faster queries
            learning_mode: Learning mode string for ReviewLog
            streak_position: Position in correct stream
        
        Returns:
            Tuple of (updated_progress, srs_result)
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Fetch or create progress
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=mode
        ).first()
        
        if not progress:
            progress = LearningProgress(
                user_id=user_id,
                item_id=item_id,
                learning_mode=mode,
                status='new',
                easiness_factor=SrsConstants.DEFAULT_EASINESS_FACTOR,
                repetitions=0,
                interval=0,
                correct_streak=0,
                incorrect_streak=0,
                first_seen=now
            )
            db.session.add(progress)
            db.session.flush()  # Get ID
        
        # 2. Process answer through UnifiedSrsSystem
        result = UnifiedSrsSystem.process_answer(
            current_status=progress.status or 'new',
            current_interval=progress.interval or 0,
            current_ef=progress.easiness_factor or SrsConstants.DEFAULT_EASINESS_FACTOR,
            current_reps=progress.repetitions or 0,
            current_correct_streak=progress.correct_streak or 0,
            current_incorrect_streak=progress.incorrect_streak or 0,
            last_reviewed=progress.last_reviewed,
            quality=quality,
            mode=mode,
            is_first_time=is_first_time,
            response_time_seconds=response_time_seconds,
            # Spec v8 fields from mode_data
            custom_state=progress.mode_data.get('custom_state', 'new') if progress.mode_data else 'new',
            hard_streak=progress.mode_data.get('hard_streak', 0) if progress.mode_data else 0,
            learning_reps=progress.mode_data.get('learning_reps', 0) if progress.mode_data else 0,
            precise_interval=progress.mode_data.get('precise_interval', 20.0) if progress.mode_data else 20.0
        )
        
        # 3. Apply results to progress
        # CRAM LOGIC: If cramming AND already learned (status != new), 
        # only update stats/history, NOT schedule.
        should_update_schedule = True
        if is_cram and progress.status != 'new':
            should_update_schedule = False
            
        if should_update_schedule:
            progress.status = result.status
            progress.interval = result.interval_minutes
            progress.easiness_factor = result.easiness_factor
            progress.repetitions = result.repetitions
            progress.due_time = result.next_review
            
            # Persist Spec v8 fields to mode_data
            if progress.mode_data is None:
                progress.mode_data = {}
            progress.mode_data['custom_state'] = result.custom_state
            progress.mode_data['hard_streak'] = result.hard_streak
            progress.mode_data['learning_reps'] = result.learning_reps
            progress.mode_data['precise_interval'] = result.precise_interval
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(progress, 'mode_data')

        progress.correct_streak = result.correct_streak
        progress.incorrect_streak = result.incorrect_streak
        
        # Always update last_reviewed (this is key for Retention/Memory Power)
        progress.last_reviewed = now
        
        # Store mastery for quick access
        progress.mastery = result.mastery
        
        # Update legacy counters
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
        
        # 4. Log to ReviewLog
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            duration_ms=duration_ms,
            interval=progress.interval,  # Use actual interval (whether updated or not)
            easiness_factor=progress.easiness_factor,
            review_type=mode,
            mastery_snapshot=result.mastery,
            memory_power_snapshot=result.memory_power,
            score_change=result.score_points,
            is_correct=(quality >= 3),
            # Session context fields
            session_id=session_id,
            container_id=container_id,
            mode=learning_mode or mode,
            streak_position=streak_position or result.correct_streak
        )
        db.session.add(log_entry)
        
        return progress, result
    
    # === LEGACY: Unified Update Method (Deprecated - use update_unified instead) ===

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
            is_correct=is_correct,
            # Session context - populated as None for legacy calls
            session_id=None,
            container_id=None,
            mode=source_mode,
            streak_position=progress.correct_streak if is_correct else 0 if hasattr(progress, 'correct_streak') else 0
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
            is_correct=is_correct,
            # Session context - populated as None for legacy calls
            session_id=None,
            container_id=None,
            mode=source_mode,
            streak_position=new_state.correct_streak if is_correct else 0
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
            dict: Summary (quality, status, next_review, score_change, points_breakdown, memory_power, updated_total_score)
        """
        # 0. Capture old state for delta calculations
        progress_old = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode=mode
        ).first()

        # Capture old mastery for UI feedback delta (using mastery avoids retention-reset confusion)
        old_mastery_pct = round((progress_old.mastery or 0.0) * 100, 1) if progress_old else 0.0

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
        
        # 3. Calculate Score using ScoringEngine with Dynamic Config
        base_points_config_key = None
        mode_lower = mode.lower()
        
        if mode_lower == 'typing':
            base_points_config_key = 'VOCAB_TYPING_CORRECT_BONUS'
        elif mode_lower == 'matching':
            base_points_config_key = 'VOCAB_MATCHING_CORRECT_BONUS'
        elif mode_lower == 'listening':
            base_points_config_key = 'VOCAB_LISTENING_CORRECT_BONUS'
        elif mode_lower == 'speed' or mode_lower == 'speed_review':
            base_points_config_key = 'VOCAB_SPEED_CORRECT_BONUS'
        elif mode_lower in ['mcq', 'quiz_mcq', 'quiz']:
             base_points_config_key = 'VOCAB_MCQ_CORRECT_BONUS'
        
        base_points_override = None
        if base_points_config_key:
             base_points_override = current_app.config.get(base_points_config_key)

        is_correct = SrsEngine.is_correct(quality)
        
        # We need correct_streak for bonus calculation (it was just updated in step 2)
        current_streak = progress.correct_streak if progress else 0
        
        score_result = ScoringEngine.calculate_answer_points(
            mode=mode,
            quality=quality,
            is_correct=is_correct,
            is_first_time=(progress.repetitions == 1 and is_correct), # Approximation
            correct_streak=current_streak,
            response_time_seconds=result_data.get('duration_ms', 0) / 1000.0,
            base_points_override=base_points_override
        )
        
        score_change = score_result.total_points

        # 4. Update the latest ReviewLog with the accurate calculated score
        # (The update() method created a log with a basic score, we refine it here)
        latest_log = ReviewLog.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).order_by(ReviewLog.timestamp.desc()).first()
        
        if latest_log:
            latest_log.score_change = score_change
            # We could also save breakdown if ReviewLog had a JSON field for it, but for now just score.
            db.session.add(latest_log)
        
        # 5. Award Points and get updated total
        from mindstack_app.modules.gamification.services.scoring_service import ScoreService
        award_result = ScoreService.award_points(
            user_id=user_id,
            amount=score_change,
            reason=f"{mode.upper()} Answer (Quality: {quality})",
            item_id=item_id,
            item_type='VOCABULARY_ITEM' # generic for vocab items
        )
        if award_result.get('success') and award_result.get('new_total') is not None:
            updated_total_score = award_result.get('new_total')
        else:
            # Fallback for amount=0 or failure
            user = User.query.get(user_id)
            updated_total_score = user.total_score if user else 0

        # Calculate new mastery for UI delta
        new_mastery_pct = round((progress.mastery or 0.0) * 100, 1)

        return {
            'quality': quality,
            'status': progress.status,
            'is_correct': is_correct,
            'next_review': progress.due_time.isoformat() if progress.due_time else None,
            'score_change': score_change,
            'points_breakdown': score_result.breakrate if hasattr(score_result, 'breakrate') else score_result.breakdown, 
            'updated_total_score': updated_total_score,
            'memory_power': {
                'mastery': new_mastery_pct,
                'memory_power': new_mastery_pct,  # Use mastery for interaction feedback
                'old_memory_power': old_mastery_pct,
                'correct_streak': progress.correct_streak,
                'interval_minutes': progress.interval
            }
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
    
    # === NEW: Batch Statistics Methods (Using UnifiedSrsSystem) ===
    
    @staticmethod
    def get_item_stats(progress: LearningProgress) -> dict:
        """
        Get real-time statistics for a single item using UnifiedSrsSystem.
        
        Args:
            progress: LearningProgress record
        
        Returns:
            Dict with mastery, retention, memory_power, is_due
        """
        return UnifiedSrsSystem.get_current_stats(
            status=progress.status,
            repetitions=progress.repetitions,
            correct_streak=progress.correct_streak or 0,
            incorrect_streak=progress.incorrect_streak or 0,
            last_reviewed=progress.last_reviewed,
            interval=progress.interval or 0,
            due_time=progress.due_time
        )
    
    @staticmethod
    def get_container_stats(user_id: int, container_id: int, mode: Optional[str] = None) -> dict:
        """
        Get aggregate statistics for a container (e.g., flashcard set).
        
        Uses UnifiedSrsSystem.calculate_batch_stats() for efficiency.
        
        Args:
            user_id: User ID
            container_id: Container ID
            mode: Optional filter by learning mode
        
        Returns:
            Dict with aggregate stats: total_items, average_memory_power,
            strong_items, medium_items, weak_items, due_items
        """
        from ..services.progress_service import ProgressService
        
        # Fetch all progress records for this container
        progress_records = ProgressService.get_all_progress_for_user(
            user_id=user_id,
            mode=mode,
            container_id=container_id
        )
        
        # Use UnifiedSrsSystem for efficient batch calculation
        return UnifiedSrsSystem.calculate_batch_stats(progress_records)


    # === Chart Data Methods ===

    @staticmethod
    def get_container_history(user_id: int, container_id: int, days: int = 30, mode: str = 'flashcard') -> dict:
        """
        Get historical memory power data for a container (for charts).
        
        Returns daily average memory power for the past N days.
        
        Args:
            user_id: User ID
            container_id: Container ID
            days: Number of days to look back
            mode: Learning mode filter
            
        Returns:
            Dict with 'dates' and 'values' arrays for charting
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Query ReviewLog for this container's items in the date range
        from ..services.progress_service import ProgressService
        
        # Get all items in this container
        item_ids_query = db.session.query(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        )
        
        # Query review logs grouped by date
        reviews = db.session.query(
            func.date(ReviewLog.timestamp).label('review_date'),
            func.avg(ReviewLog.memory_power_snapshot).label('avg_memory_power')
        ).filter(
            ReviewLog.user_id == user_id,
            ReviewLog.item_id.in_(item_ids_query),
            ReviewLog.timestamp >= start_date
        ).group_by(
            func.date(ReviewLog.timestamp)
        ).order_by('review_date').all()
        
        # Build response
        dates = []
        values = []
        
        # Fill in missing dates with None or previous value
        current_date = start_date.date()
        review_dict = {r.review_date: float(r.avg_memory_power * 100) if r.avg_memory_power else 0 for r in reviews}
        
        while current_date <= end_date.date():
            dates.append(current_date.strftime('%Y-%m-%d'))
            values.append(review_dict.get(current_date, None))
            current_date += timedelta(days=1)
        
        return {
            'dates': dates,
            'values': values
        }

    @staticmethod
    def get_item_review_history(item_id: int, user_id: int, limit: int = 50) -> list:
        """
        Get review history for an individual item (for charts).
        
        Returns list of reviews with timestamp, quality, memory_power.
        
        Args:
            item_id: Learning item ID
            user_id: User ID
            limit: Maximum number of reviews to return
            
        Returns:
            List of dicts with review data
        """
        # Query ReviewLog for this item
        reviews = ReviewLog.query.filter_by(
            item_id=item_id,
            user_id=user_id
        ).order_by(
            ReviewLog.timestamp.desc()
        ).limit(limit).all()
        
        # Reverse to get chronological order
        reviews = list(reversed(reviews))
        
        # Build response
        history = []
        for review in reviews:
            history.append({
                'timestamp': review.timestamp.isoformat(),
                'date': review.timestamp.strftime('%Y-%m-%d %H:%M'),
                'rating': review.rating,  # Fixed: was quality
                'memory_power': round(review.memory_power_snapshot * 100, 1) if review.memory_power_snapshot else 0,  # Fixed
                'interval': review.interval,
                'ease_factor': review.easiness_factor  # Fixed: was ease_factor
            })
        
        return history

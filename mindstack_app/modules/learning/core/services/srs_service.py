"""
SRS (Spaced Repetition System) Business Logic.
Encapsulates algorithms for calculating intervals, easiness factors, and updating item progress.
"""

import datetime
from typing import Optional, Tuple
from mindstack_app.models import db, FlashcardProgress, LearningItem
from sqlalchemy.orm.attributes import flag_modified

# Constants derived from original flashcard_logic.py
LEARNING_STEPS_MINUTES = [10, 60, 240, 480, 1440, 2880]
RELEARNING_STEP_MINUTES = 10
GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60  # 4 days
MIN_EASINESS_FACTOR = 1.3

class SrsService:
    @staticmethod
    def _get_next_learning_interval(repetitions: int) -> int:
        """Get interval for learning phase based on step index."""
        step_index = repetitions - 1
        if 0 <= step_index < len(LEARNING_STEPS_MINUTES):
            return LEARNING_STEPS_MINUTES[step_index]
        return LEARNING_STEPS_MINUTES[-1]

    @staticmethod
    def calculate_next_state(
        current_status: str,
        current_interval: int,
        current_ef: float,
        current_reps: int,
        quality: int
    ) -> Tuple[str, int, float, int]:
        """
        Pure function to calculate next SRS state.
        Returns: (new_status, new_interval_minutes, new_ef, new_reps)
        """
        new_status = current_status
        new_interval = current_interval
        new_ef = current_ef
        new_reps = current_reps

        if current_status in ['learning', 'new']:
            if quality < 3:
                new_interval = RELEARNING_STEP_MINUTES
                # Repetitions might not reset in learning, or logic implies staying at start?
                # Original logic: _get_next_learning_interval uses current_reps.
                # If quality < 3, strictly set to 10 mins.
            else:
                new_reps = current_reps  # Incrementing handled by caller usually? No, let's assume caller incremented pre-call? 
                # Wait, original logic relied on caller to increment `repetitions` BEFORE calling `calculate_next_review_time`?
                # Let's check original logic:
                # if is_correct: progress.repetitions += 1
                # THEN progress.due_time = calculate_next...(progress)
                # So here we assume input `current_reps` is ALREADY incremented if correct.
                
                new_interval = SrsService._get_next_learning_interval(current_reps)
        
        elif current_status == 'reviewing':
            if quality < 3:
                new_interval = RELEARNING_STEP_MINUTES
                # Original logic: status -> learning, refs -> 0. Handled by caller?
                # The caller should handle status transitions logic ideally, or this function does EVERYTHING.
                # Let's make this function do EVERYTHING state transition wise.
                new_status = 'learning'
                new_reps = 0
                new_ef = max(MIN_EASINESS_FACTOR, current_ef - 0.2)
            else:
                # Recalculate EF
                # q = quality (0-5)
                # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q)*0.02))
                q = quality
                new_ef = current_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
                if new_ef < MIN_EASINESS_FACTOR:
                    new_ef = MIN_EASINESS_FACTOR
                
                # Interval
                import math
                new_interval = math.ceil(current_interval * new_ef)
                # Reps already incremented by caller? 
                # Let's stick to the pattern: Input state -> Output state.
                # If quality >= 3, we expect reps to increase.
                new_reps = current_reps + 1

        return new_status, new_interval, new_ef, new_reps

    @staticmethod
    def update_item_progress(user_id: int, item_id: int, quality: int, source_mode: str = 'flashcard') -> FlashcardProgress:
        """
        Main entry point to update progress for an item.
        Handles checking/creating record and applying SRS logic.
        Commit is left to caller safely.
        """
        progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
        now = datetime.datetime.now(datetime.timezone.utc)

        if not progress:
            progress = FlashcardProgress(
                user_id=user_id, item_id=item_id, status='new',
                easiness_factor=2.5, repetitions=0, interval=0,
                first_seen_timestamp=now
            )
            db.session.add(progress)
        
        # Ensure timezone aware
        if progress.first_seen_timestamp and progress.first_seen_timestamp.tzinfo is None:
            progress.first_seen_timestamp = progress.first_seen_timestamp.replace(tzinfo=datetime.timezone.utc)

        # Update stats
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1

        # Check early review
        due_time = progress.due_time
        if due_time and due_time.tzinfo is None:
            due_time = due_time.replace(tzinfo=datetime.timezone.utc)
        
        is_early_review = due_time and now < due_time

        # If early review, don't update interval, just log
        if is_early_review:
            # Only update last_reviewed
            progress.last_reviewed = now
        else:
            # Full SRS Update
            if progress.status == 'new':
                progress.status = 'learning'
            
            # Prepare inputs
            # Note: For 'learning' -> 'reviewing' transition logic (graduation)
            # Original logic: if learning && reps >= 7 && avg_quality > 3 -> reviewing
            # We defer that complex check or include it?
            # Let's stick to basic algorithm first, then checks graduation.

            # We need to handle the state transitions carefully to match original logic.
            # Original:
            # If status == 'reviewing':
            #   if incorrect: status='learning', reps=0, ef-=0.2
            #   else: reps+=1, calc ef, calc interval
            # If status == 'learning':
            #   if incorrect: reps=0
            #   else: reps+=1
            #   calc interval
            
            current_status = progress.status
            current_reps = progress.repetitions or 0
            current_ef = progress.easiness_factor or 2.5
            current_interval = progress.interval or 0

            # Pre-calc Reps logic from original:
            # if reviewing & correct: reps+1
            # if learning & correct: reps+1
            # if incorrect: reps=0 (learning) or reset (reviewing)
            
            # Actually, `calculate_next_state` above tries to be smart but might be confusing.
            # Let's replicate exact logic flow here for safety.

            import math

            new_status = current_status
            new_reps = current_reps
            new_ef = current_ef
            new_interval = current_interval

            if current_status == 'reviewing':
                if quality < 3:
                    new_status = 'learning'
                    new_reps = 0
                    new_ef = max(MIN_EASINESS_FACTOR, current_ef - 0.2)
                    new_interval = RELEARNING_STEP_MINUTES
                else:
                    new_reps = current_reps + 1
                    # Recalculate EF
                    q = quality
                    new_ef = current_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
                    if new_ef < MIN_EASINESS_FACTOR: new_ef = MIN_EASINESS_FACTOR
                    
                    new_interval = math.ceil(current_interval * new_ef)
            else: # new or learning
                if quality < 3:
                    new_reps = 0 # specific to original logic? 
                    # Original: if is_incorrect_response: progress.repetitions = 0
                    new_interval = RELEARNING_STEP_MINUTES
                else:
                    new_reps = current_reps + 1
                    # get learning interval
                    step_index = new_reps - 1
                    if 0 <= step_index < len(LEARNING_STEPS_MINUTES):
                        new_interval = LEARNING_STEPS_MINUTES[step_index]
                    else:
                        new_interval = LEARNING_STEPS_MINUTES[-1]

            # Apply changes
            progress.status = new_status
            progress.repetitions = new_reps
            progress.easiness_factor = new_ef
            progress.interval = new_interval
            progress.last_reviewed = now
            progress.due_time = now + datetime.timedelta(minutes=new_interval)


            # Check Graduation (Learning -> Reviewing)
            if progress.status == 'learning':
                # Need review history for average calculation?
                # For efficiency/simplicity in this Service, we might skip the deep history check 
                # unless we load it. Original logic filtered history.
                # Let's do a simplified check: if repetitions > 6 (meaning 7th successful rep)
                if progress.repetitions >= 7 and quality >= 4:
                     progress.status = 'reviewing'
                     progress.interval = GRADUATING_INTERVAL_MINUTES
                     progress.due_time = now + datetime.timedelta(minutes=progress.interval)
                     progress.repetitions = 1
        
        # Log History
        if progress.review_history is None:
            progress.review_history = []
        
        entry = {
            'timestamp': now.isoformat(),
            'user_answer_quality': quality,
            'source': source_mode
        }
        progress.review_history.append(entry)
        flag_modified(progress, "review_history")

        return progress

    # === NEW: Memory Power System ===

    @staticmethod
    def update_with_memory_power(
        user_id: int,
        item_id: int,
        quality: int,
        source_mode: str = 'flashcard'
    ) -> FlashcardProgress:
        """
        Update progress using Memory Power system.
        
        This method uses the new MemoryEngine for calculations instead of
        the legacy SM-2 algorithm. It provides:
        - Streak-based mastery calculation
        - Compounding penalties for consecutive errors
        - Memory power = mastery × retention
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (0-5)
            source_mode: Source of the review ('flashcard', 'quiz', 'typing')
            
        Returns:
            Updated FlashcardProgress instance
        """
        from mindstack_app.modules.learning.core.logics.memory_engine import (
            MemoryEngine, ProgressState
        )
        from mindstack_app.models import ReviewLog
        
        progress = FlashcardProgress.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        is_new = False
        if not progress:
            is_new = True
            progress = FlashcardProgress(
                user_id=user_id,
                item_id=item_id,
                status='new',
                easiness_factor=2.5,
                repetitions=0,
                interval=0,
                mastery=0.0,
                correct_streak=0,
                incorrect_streak=0,
                first_seen_timestamp=now
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
            easiness_factor=progress.easiness_factor or 2.5
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
        
        # Update legacy counters for compatibility
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
        
        # Log to ReviewLog table
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            interval=new_state.interval,
            easiness_factor=new_state.easiness_factor,
            review_type=source_mode
        )
        db.session.add(log_entry)
        
        # Also maintain legacy review_history for backward compatibility
        if progress.review_history is None:
            progress.review_history = []
        
        history_entry = {
            'timestamp': now.isoformat(),
            'user_answer_quality': quality,
            'source': source_mode,
            'mastery': new_state.mastery,
            'memory_power': result.memory_power
        }
        progress.review_history.append(history_entry)
        flag_modified(progress, "review_history")
        
        return progress

    @staticmethod
    def get_memory_power(progress: FlashcardProgress) -> float:
        """
        Calculate current Memory Power for a progress record.
        
        Returns:
            Memory Power percentage (0.0 - 1.0)
        """
        from mindstack_app.modules.learning.core.logics.memory_engine import MemoryEngine
        
        if not progress:
            return 0.0
        
        mastery = progress.mastery or 0.0
        retention = MemoryEngine.calculate_retention(
            progress.last_reviewed,
            progress.interval or 0
        )
        
        return MemoryEngine.calculate_memory_power(mastery, retention)

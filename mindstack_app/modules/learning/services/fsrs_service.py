"""
FSRS Service - Pure FSRS-5 Database Layer

Handles database persistence for FSRS operations.
Delegates all calculations to HybridFSRSEngine.
"""

import datetime
import math
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from flask import current_app
from mindstack_app.models import db, LearningItem, ReviewLog, User
from mindstack_app.models.learning_progress import LearningProgress

from ..logics.scoring_engine import ScoringEngine
from ..logics.hybrid_fsrs import HybridFSRSEngine, CardState, Rating


@dataclass
class SrsResult:
    """Result of processing a learning interaction."""
    next_review: datetime.datetime
    interval_minutes: int
    state: int  # 0=New, 1=Learning, 2=Review, 3=Relearning
    stability: float
    difficulty: float
    retrievability: float  # Current recall probability (0.0-1.0)
    correct_streak: int
    incorrect_streak: int
    score_points: int
    score_breakdown: Dict[str, int]
    repetitions: int


class FsrsService:
    """
    Service layer for pure FSRS-5 operations.
    No legacy SM2 fallbacks.
    """

    @staticmethod
    def process_answer(
        user_id: int,
        item_id: int,
        quality: int,  # FSRS rating 1-4 (Again/Hard/Good/Easy)
        mode: str = 'flashcard',
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None,
        duration_ms: int = 0,
        is_cram: bool = False,
        session_id: int = None,
        container_id: int = None,
        learning_mode: str = None,
        streak_position: int = 0,
        **kwargs
    ) -> Tuple[LearningProgress, SrsResult]:
        """
        Process a learning answer using Pure FSRS-5.
        
        Args:
            quality: FSRS Rating 1=Again, 2=Hard, 3=Good, 4=Easy
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
                fsrs_state=LearningProgress.STATE_NEW,
                fsrs_stability=0.0,
                fsrs_difficulty=5.0,
                repetitions=0,
                current_interval=0.0,
                correct_streak=0,
                incorrect_streak=0
            )
            db.session.add(progress)
            db.session.flush()

        # 2. Build CardState from native columns
        last_review = progress.fsrs_last_review
        if last_review and last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
        
        # Use native integer state directly
        current_state_int = progress.fsrs_state if progress.fsrs_state is not None else LearningProgress.STATE_NEW
        
        card = CardState(
            stability=progress.fsrs_stability or 0.0,
            difficulty=progress.fsrs_difficulty or 0.0,
            reps=progress.repetitions or 0,
            lapses=progress.lapses or 0,
            state=current_state_int,
            last_review=last_review
        )

        # 3. Process with FSRS Engine
        from mindstack_app.services.memory_power_config_service import MemoryPowerConfigService
        desired_retention = MemoryPowerConfigService.get('FSRS_DESIRED_RETENTION', 0.9)
        
        engine = HybridFSRSEngine(desired_retention=desired_retention)
        new_card, next_due, log_info = engine.review_card(
            card_state=card,
            rating=quality,
            now=now
        )
        
        # 4. Calculate correctness and scoring
        is_correct = quality >= Rating.Good
        current_streak = progress.correct_streak or 0
        new_correct_streak = current_streak + 1 if is_correct else 0
        new_incorrect_streak = (progress.incorrect_streak or 0) + 1 if not is_correct else 0
        
        score_result = ScoringEngine.calculate_answer_points(
            mode=mode,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=new_correct_streak,
            response_time_seconds=response_time_seconds
        )
        
        # 5. Calculate retrievability (resets to ~1.0 after correct answer)
        new_retrievability = 1.0 if is_correct else 0.9
        
        # 6. Extract results (No string conversion needed)
        new_state_int = new_card.state
        interval_minutes = int(new_card.scheduled_days * 1440)
        
        srs_result = SrsResult(
            next_review=next_due,
            interval_minutes=interval_minutes,
            state=new_state_int,
            stability=new_card.stability,
            difficulty=new_card.difficulty,
            retrievability=new_retrievability,
            correct_streak=new_correct_streak,
            incorrect_streak=new_incorrect_streak,
            score_points=score_result.total_points,
            score_breakdown=score_result.breakdown,
            repetitions=new_card.reps
        )

        # 7. Save to Progress (skip schedule update for cram mode)
        should_update_schedule = not (is_cram and progress.fsrs_state != LearningProgress.STATE_NEW)
        
        if should_update_schedule:
            progress.fsrs_state = new_state_int
            progress.fsrs_stability = new_card.stability
            progress.fsrs_difficulty = new_card.difficulty
            progress.current_interval = new_card.scheduled_days # Store in days (Float) or continue utilizing interval column? Model says current_interval=Float days.
            # Sync legacy interval column (minutes) if needed, or just set current_interval
            # progress.interval = interval_minutes # Legacy column might be gone or repurposed.
            # Let's rely on current_interval (Float days) as per my model refactor.
            progress.current_interval = float(new_card.scheduled_days)
            
            progress.repetitions = new_card.reps
            progress.lapses = new_card.lapses
            progress.fsrs_due = next_due
            progress.fsrs_last_review = now
            progress.last_review_duration = duration_ms
            
        progress.correct_streak = new_correct_streak
        progress.incorrect_streak = new_incorrect_streak
        
        # Update counters
        if is_correct:
            progress.times_correct = (progress.times_correct or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
        
        # 8. Log Review
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            
            # FSRS Optimizer Fields
            scheduled_days=new_card.scheduled_days,
            elapsed_days=log_info.get('days_elapsed', 0.0),
            review_duration=duration_ms,
            state=current_state_int, # State BEFORE review
            
            # Snapshots
            fsrs_stability=new_card.stability,
            fsrs_difficulty=new_card.difficulty,
            
            review_type=mode,
            score_change=score_result.total_points,
            is_correct=is_correct,
            session_id=session_id,
            container_id=container_id,
            mode=learning_mode or mode,
            streak_position=streak_position or new_correct_streak
        )
        db.session.add(log_entry)
        
        return progress, srs_result

    @staticmethod
    def get_retrievability(progress: LearningProgress) -> float:
        """
        Calculate current retrievability using pure FSRS formula.
        
        Formula: R = 0.9^(elapsed_days / stability)
        
        Returns:
            Retrievability (0.0 - 1.0)
        """
        if not progress or progress.fsrs_stability is None or progress.fsrs_stability <= 0:
            return 1.0
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if not progress.fsrs_last_review:
            return 1.0
        
        last_review = progress.fsrs_last_review
        if last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
        
        elapsed_days = (now - last_review).total_seconds() / 86400.0
        if elapsed_days <= 0:
            return 1.0
        
        try:
            return 0.9 ** (elapsed_days / progress.fsrs_stability)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    # Legacy alias
    get_memory_power = get_retrievability

    @staticmethod
    def get_item_stats(progress: LearningProgress) -> dict:
        """Get real-time statistics for a single item."""
        if not progress:
            return {'stability': 0, 'retrievability': 1.0, 'is_due': True}

        now = datetime.datetime.now(datetime.timezone.utc)
        retrievability = FsrsService.get_retrievability(progress)
        
        if progress.fsrs_due:
            due_aware = progress.fsrs_due.replace(tzinfo=datetime.timezone.utc) if progress.fsrs_due.tzinfo is None else progress.fsrs_due
            is_due = now >= due_aware
        else:
            is_due = True
            
        return {
            'stability': progress.fsrs_stability or 0,
            'difficulty': progress.fsrs_difficulty or 5.0,
            'retrievability': retrievability,
            'is_due': is_due,
            'state': progress.fsrs_state
        }

    @staticmethod
    def calculate_batch_stats(progress_records: list, now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """Calculate aggregate statistics for multiple items."""
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        
        if not progress_records:
            return {
                'total_items': 0,
                'average_retrievability': 0,
                'strong_items': 0,
                'medium_items': 0,
                'weak_items': 0,
                'due_items': 0
            }
        
        stats_list = []
        for progress in progress_records:
            stability = progress.fsrs_stability or 0.1
            
            # Calculate retrievability
            if progress.fsrs_last_review and stability > 0:
                last_review = progress.fsrs_last_review
                if last_review.tzinfo is None:
                    last_review = last_review.replace(tzinfo=datetime.timezone.utc)
                elapsed_days = (now - last_review).total_seconds() / 86400.0
                retrievability = 0.9 ** (elapsed_days / stability) if elapsed_days > 0 else 1.0
            else:
                retrievability = 1.0
            
            if progress.fsrs_due:
                due_aware = progress.fsrs_due.replace(tzinfo=datetime.timezone.utc) if progress.fsrs_due.tzinfo is None else progress.fsrs_due
                is_due = now >= due_aware
            else:
                is_due = True
            
            stats_list.append({
                'retrievability': retrievability,
                'is_due': is_due
            })
        
        total_items = len(stats_list)
        avg_r = sum(s['retrievability'] for s in stats_list) / total_items
        strong = len([s for s in stats_list if s['retrievability'] >= 0.8])
        medium = len([s for s in stats_list if 0.5 <= s['retrievability'] < 0.8])
        weak = len([s for s in stats_list if s['retrievability'] < 0.5])
        due = len([s for s in stats_list if s['is_due']])
        
        return {
            'total_items': total_items,
            'average_retrievability': round(avg_r, 4),
            'strong_items': strong,
            'medium_items': medium,
            'weak_items': weak,
            'due_items': due
        }

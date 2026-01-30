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
from sqlalchemy import func
from mindstack_app.models import db, LearningItem, ReviewLog, User
from mindstack_app.models.learning_progress import LearningProgress

from ..logics.scoring_engine import ScoringEngine
from ..logics.hybrid_fsrs import HybridFSRSEngine, CardState, Rating
from fsrs_rs_python import DEFAULT_PARAMETERS

from mindstack_app.core.signals import card_reviewed


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
    def _normalize_rating(quality: Any) -> int:
        """
        Normalize legacy SM-2 ratings (0-5) or None to FSRS v5 strict ratings (1-4).
        
        Mapping logic (FSRS v5 standard):
        - None, 0, 1 -> 1 (Again)
        - 2          -> 2 (Hard)
        - 3          -> 3 (Good)
        - 4, 5       -> 4 (Easy)
        - > 5        -> 4 (Safety clamp)
        """
        if quality is None:
            return 1
        
        try:
            q = int(quality)
        except (ValueError, TypeError):
            return 1

        if q <= 1:
            return 1
        elif q == 2:
            return 2
        elif q == 3:
            return 3
        else:
            return 4

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return FsrsService._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    @staticmethod
    def _calculate_quiz_rating(is_correct: bool, duration_ms: int) -> int:
        """
        Derive FSRS Rating (1-4) from Quiz (MCQ) performance.
        - Incorrect -> Again (1)
        - Correct & < 3s -> Easy (4)
        - Correct & 3-10s -> Good (3)
        - Correct & > 10s -> Hard (2)
        """
        if not is_correct:
            return Rating.Again
        
        from mindstack_app.modules.learning.services.memory_power_config_service import MemoryPowerConfigService
        easy_threshold = MemoryPowerConfigService.get('QUIZ_RATING_EASY_MS', 3000)
        good_threshold = MemoryPowerConfigService.get('QUIZ_RATING_GOOD_MS', 10000)
        
        if duration_ms < easy_threshold:
            return Rating.Easy
        elif duration_ms <= good_threshold:
            return Rating.Good
        else:
            return Rating.Hard

    @staticmethod
    def _calculate_typing_rating(target_text: str, user_answer: str, duration_ms: int) -> int:
        """
        Derive FSRS Rating (1-4) from Typing performance.
        Logic:
        - Perfect match + high speed -> Easy (4)
        - Perfect match + normal speed -> Good (3)
        - Minor typos (similarity >= 0.8) -> Hard (2)
        - Major errors (similarity < 0.8) -> Again (1)
        """
        if not target_text or not user_answer:
            return Rating.Again
            
        t = target_text.strip().lower()
        u = user_answer.strip().lower()
        
        if t == u:
            # Calculate WPM assuming 5 chars per word
            # WPM = (chars / 5) / (ms / 60000)
            if duration_ms > 0:
                wpm = (len(t) / 5.0) / (duration_ms / 60000.0)
                if wpm >= 40: # Rapid recall
                    return Rating.Easy
            return Rating.Good
            
        # Minor typos
        distance = FsrsService._levenshtein_distance(t, u)
        max_len = max(len(t), len(u), 1)
        similarity = 1.0 - (distance / max_len)
        
        if similarity >= 0.8:
            return Rating.Hard
            
        return Rating.Again

    @staticmethod
    def _get_effective_parameters(user_id: int) -> list[float]:
        """
        Determine the effective FSRS parameters (weights) for a user.
        
        Priority:
        1. User-Specific Parameters (from Optimizer)
        2. Global Admin Configuration (from AppSettings)
        3. Library Defaults (from fsrs-rs-python)
        """
        # Tier 1: User Specific
        user_params = None
        try:
            from .fsrs_optimizer import FsrsOptimizerService
            user_params = FsrsOptimizerService.get_user_parameters(user_id)
            
            if user_params and isinstance(user_params, list) and len(user_params) == 19:
                current_app.logger.debug(f"Using Tier 1 (User-Specific) FSRS parameters for user {user_id}")
                return user_params
        except Exception:
            pass # Fallthrough if optimizer service fails or data invalid

        # Tier 2: Global Admin Config
        from mindstack_app.modules.learning.services.memory_power_config_service import MemoryPowerConfigService
        global_params = MemoryPowerConfigService.get('FSRS_GLOBAL_WEIGHTS')
        
        # Validate global params
        if global_params and isinstance(global_params, list) and len(global_params) == 19:
            # Ensure all are numbers
            try:
                global_params = [float(x) for x in global_params]
                current_app.logger.debug(f"Using Tier 2 (Global Config) FSRS parameters for user {user_id}")
                return global_params
            except (ValueError, TypeError):
                current_app.logger.warning("Tier 2 FSRS parameters invalid (not numbers), falling back to default.")

        # Tier 3: Library Defaults
        current_app.logger.debug(f"Using Tier 3 (Library Defaults) FSRS parameters for user {user_id}")
        return list(DEFAULT_PARAMETERS)

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
        # 0. Mode-Based FSRS v5 Rating Calculation
        if mode in ['quiz', 'quiz_mcq']:
            is_correct_arg = kwargs.get('is_correct', quality >= 3 if quality is not None else False)
            fsrs_rating = FsrsService._calculate_quiz_rating(is_correct_arg, duration_ms)
        elif mode in ['typing', 'listening']:
            target_text = kwargs.get('target_text', '')
            user_answer = kwargs.get('user_answer', '')
            fsrs_rating = FsrsService._calculate_typing_rating(target_text, user_answer, duration_ms)
        else:
            # Default or Flashcard: Maps legacy 0-5 or None to strict 1-4
            fsrs_rating = FsrsService._normalize_rating(quality)
        
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
            last_review=last_review,
            # [FIX] Load scheduled_days from float column (source of truth)
            scheduled_days=progress.current_interval or 0.0
        )

        # Fetch Configuration with Caps
        from mindstack_app.modules.learning.services.memory_power_config_service import MemoryPowerConfigService
        from mindstack_app.services.container_config_service import ContainerConfigService
        
        # Priority: Container-specific retention -> Global retention
        container_retention = ContainerConfigService.get_retention(container_id)
        if container_retention is not None:
             current_app.logger.debug(f"Using container-specific retention {container_retention} for container {container_id}")
             desired_retention = container_retention
        else:
             desired_retention = float(MemoryPowerConfigService.get('FSRS_DESIRED_RETENTION', 0.9))
        
        # Safety clamp
        desired_retention = max(0.70, min(0.99, desired_retention))
        
        enable_fuzz = bool(MemoryPowerConfigService.get('FSRS_ENABLE_FUZZ', False))
        max_interval_days = int(MemoryPowerConfigService.get('FSRS_MAX_INTERVAL', 365))
        
        effective_weights = FsrsService._get_effective_parameters(user_id)

        engine = HybridFSRSEngine(
            desired_retention=desired_retention, 
            custom_weights=effective_weights
        )
        
        new_card, next_due, log_info = engine.review_card(
            card_state=card,
            rating=fsrs_rating,
            now=now,
            enable_fuzz=enable_fuzz
        )
        
        # [FIX] Enforce Admin Max Interval Cap (Post-Engine)
        if new_card.scheduled_days > max_interval_days:
            current_app.logger.debug(f"Capping interval {new_card.scheduled_days:.2f} to max {max_interval_days}")
            new_card.scheduled_days = float(max_interval_days)
            # Recalculate due date based on capped interval
            next_due = now + datetime.timedelta(days=max_interval_days)
            new_card.due = next_due

        
        # 4. Calculate correctness and scoring
        # Use normalized quality for FSRS logic, but original quality might be relevant for scoring?
        # Scoring usually expects 0-5. 'quality' argument is preserved.
        is_correct = fsrs_rating >= Rating.Good
        current_streak = progress.correct_streak or 0
        new_correct_streak = current_streak + 1 if is_correct else 0
        new_incorrect_streak = (progress.incorrect_streak or 0) + 1 if not is_correct else 0
        
        score_result = ScoringEngine.calculate_answer_points(
            mode=mode,
            quality=fsrs_rating, # Use normalized FSRS rating (1-4)
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=new_correct_streak,
            response_time_seconds=response_time_seconds,
            stability=card.stability,
            difficulty=card.difficulty
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

        # 7. Apply Load Balancing (Date Shifting)
        # If the target date is overloaded (> FSRS_DAILY_LIMIT), shift due date +/- 1 day for non-critical reviews.
        daily_limit = int(MemoryPowerConfigService.get('FSRS_DAILY_LIMIT', 200))
        target_date = next_due.date()
        
        # Count existing reviews for this user on that date
        # Better: check LearningProgress.fsrs_due for future dates
        due_on_date_count = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            func.date(LearningProgress.fsrs_due) == target_date
        ).count()
        
        if due_on_date_count > daily_limit and fsrs_rating >= Rating.Good:
            import random as py_random
            shift = py_random.choice([-1, 1])
            next_due = next_due + datetime.timedelta(days=shift)
            current_app.logger.debug(f"Load Balancing: Shifted due date for item {item_id} by {shift} day(s)")

        # 8. Save to Progress (skip schedule update for cram mode)
        should_update_schedule = not (is_cram and progress.fsrs_state != LearningProgress.STATE_NEW)
        
        if should_update_schedule:
            progress.fsrs_state = new_state_int
            progress.fsrs_stability = new_card.stability
            progress.fsrs_difficulty = new_card.difficulty
            
            # [FIX] Enforce Floating-Point Precision
            progress.current_interval = float(new_card.scheduled_days)
            
            # LEGACY SUPPORT ONLY: FSRS uses 'current_interval' (float days) as the source of truth
            progress.interval = interval_minutes 
            
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
        
        # 9. Log Review
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=fsrs_rating, # MUST log normalized FSRS rating 1-4
            
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
        db.session.flush() # Ensure log is in DB for count check
        
        # 10. Automated Optimizer Trigger
        optimizer_threshold = int(MemoryPowerConfigService.get('FSRS_OPTIMIZER_THRESHOLD', 500))
        review_count = ReviewLog.query.filter_by(user_id=user_id).count()
        
        if review_count >= optimizer_threshold and review_count % optimizer_threshold == 0:
            try:
                from .fsrs_optimizer import FsrsOptimizerService
                current_app.logger.info(f"Triggering FSRS Optimization for user {user_id} (Reviews: {review_count})")
                # Run optimization (it updates user.fsrs_parameters internally)
                FsrsOptimizerService.train_for_user(user_id)
            except Exception as e:
                current_app.logger.error(f"FSRS Optimization failed for user {user_id}: {e}")
        
        # 11. Commit and emit signal for gamification integration
        db.session.commit()
        
        # Emit card_reviewed signal - gamification module listens for this
        card_reviewed.send(
            None,
            user_id=user_id,
            item_id=item_id,
            quality=fsrs_rating,
            is_correct=is_correct,
            learning_mode=mode,
            score_points=score_result.total_points,
            item_type=mode.upper(),
            reason=f'Review {mode}',
            duration_ms=duration_ms
        )
        
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

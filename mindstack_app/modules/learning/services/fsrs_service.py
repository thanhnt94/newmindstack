"""
FSRS Service - Database Layer for Spaced Repetition System (FSRS-5)

Handles database persistence for SRS operations.
Delegates all calculations to HybridFSRSEngine (FSRS-5).

This service:
- Fetches/creates LearningProgress records
- Delegates calculations to FSRS engine
- Saves results to database (LearningProgress, ReviewLog)
- Returns updated progress
"""

import datetime
import math
from typing import Optional
from flask import current_app
from mindstack_app.models import db, LearningItem, ReviewLog, User
from mindstack_app.models.learning_progress import LearningProgress

from ..logics.scoring_engine import ScoringEngine
from .fsrs_optimizer import FsrsOptimizerService
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class SrsResult:
    """Result of processing a learning interaction."""
    # Scheduling results
    next_review: datetime.datetime
    interval_minutes: int
    status: str  # 'new', 'learning', 'reviewing'
    
    # FSRS Metrics (pure FSRS-5)
    stability: float  # S - days until 90% retention drops
    retrievability: float  # R - current recall probability (0.0-1.0)
    
    # Streaks
    correct_streak: int
    incorrect_streak: int
    
    # Scoring
    score_points: int
    score_breakdown: Dict[str, int]
    
    # Internal State (for persistence)
    repetitions: int
    easiness_factor: float
    
    # Spec v8 fields
    custom_state: str = 'new'
    hard_streak: int = 0
    learning_reps: int = 0
    precise_interval: float = 20.0

# Constants for default values
class FsrsConstants:
    DEFAULT_EASINESS_FACTOR = 2.5  # Default stability for new cards
    GRADUATING_INTERVAL_MINUTES = 1440  # 1 day


class FsrsService:
    """
    Service layer for FSRS operations.
    Coordinates between database and calculation engines.
    """

    # === Process Answer (Direct FSRS-5) ===

    @staticmethod
    def process_answer(
        user_id: int,
        item_id: int,
        quality: int,  # FSRS rating 1-4
        mode: str = 'flashcard',
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None,
        duration_ms: int = 0,
        is_cram: bool = False,
        # Session context fields
        session_id: int = None,
        container_id: int = None,
        learning_mode: str = None,
        streak_position: int = 0,
        **kwargs
    ) -> Tuple[LearningProgress, SrsResult]:
        """
        Process a learning answer using Standard FSRS-5.
        
        Args:
            user_id: User ID
            item_id: Learning item ID
            quality: Answer quality (1=Again, 2=Hard, 3=Good, 4=Easy)
            mode: Learning mode ('flashcard', etc.)
            ...
        
        Returns:
            Tuple of (updated_progress, srs_result)
        """
        # Import engine locally to avoid circular deps if any
        from ..logics.hybrid_fsrs import HybridFSRSEngine, CardState, Rating
        
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
                easiness_factor=FsrsConstants.DEFAULT_EASINESS_FACTOR,
                repetitions=0,
                interval=0,
                correct_streak=0,
                incorrect_streak=0,
                first_seen=now
            )
            db.session.add(progress)
            db.session.flush()

        # 2. Prepare FSRS Input
        # Good(3) and Easy(4) are considered correct
        is_correct = quality >= Rating.Good
        
        # === READ FROM NATIVE FSRS COLUMNS ===
        # Use native columns as primary source, fallback to mode_data for unmigrated records
        if progress.fsrs_stability is not None and progress.fsrs_stability > 0:
            # Native FSRS data available
            fsrs_stability = progress.fsrs_stability
            fsrs_difficulty = progress.fsrs_difficulty or 5.0
            
            # Map state int to string
            state_map = {
                LearningProgress.FSRS_STATE_NEW: 'new',
                LearningProgress.FSRS_STATE_LEARNING: 'learning',
                LearningProgress.FSRS_STATE_REVIEW: 'review',
                LearningProgress.FSRS_STATE_RELEARNING: 're-learning',
            }
            custom_state = state_map.get(progress.fsrs_state, 'new')
            last_reviewed = progress.fsrs_last_review or progress.last_reviewed
        else:
            # Fallback: Check mode_data for legacy FSRS data
            mode_data = progress.mode_data or {}
            if 'fsrs_stability' in mode_data:
                fsrs_stability = mode_data.get('fsrs_stability', 0.0)
                fsrs_difficulty = mode_data.get('fsrs_difficulty', 5.0)
                custom_state = mode_data.get('custom_state', 'new')
            else:
                # New card - fresh start
                fsrs_stability = 0.0
                fsrs_difficulty = 5.0
                custom_state = 'new'
            last_reviewed = progress.last_reviewed
        
        if last_reviewed and last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=datetime.timezone.utc)
            
        # Build FSRS CardState
        card = CardState(
            stability=fsrs_stability,
            difficulty=fsrs_difficulty,
            reps=progress.repetitions or 0,
            last_review=last_reviewed,
            state=custom_state if custom_state in ('new', 'learning', 'review', 're-learning') else 'new'
        )

        # 3. Process with FSRS Engine
        # Read FSRS params from admin config (global settings)
        from mindstack_app.services.memory_power_config_service import MemoryPowerConfigService
        desired_retention = MemoryPowerConfigService.get('FSRS_DESIRED_RETENTION', 0.9)
        custom_weights = MemoryPowerConfigService.get('FSRS_W_PARAMS', None)
        
        engine = HybridFSRSEngine(
            desired_retention=desired_retention,
            custom_weights=custom_weights
        )
        
        new_card, next_due, log_info = engine.review_card(
            card_state=card,
            rating=quality,
            now=now
        )
        
        # 4. Score Calculation
        current_streak = progress.correct_streak if progress.correct_streak else 0
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
        
        # 5. Metrics Calculation
        # FSRS Retrievability: R = 0.9^(t/S) at time of review
        # After answering, retrievability resets to 1.0 (just recalled)
        new_retrievability = 1.0 if is_correct else 0.9
        
        # Map status
        status_map = {
            'new': 'new',
            'learning': 'learning',
            're-learning': 'learning',
            'review': 'reviewing'
        }
        new_status = status_map.get(new_card.state, 'reviewing')
        interval_minutes = int((next_due - now).total_seconds() / 60)
        
        srs_result = SrsResult(
            next_review=next_due,
            interval_minutes=interval_minutes,
            status=new_status,
            stability=round(new_card.stability, 4),
            retrievability=round(new_retrievability, 4),
            correct_streak=new_correct_streak,
            incorrect_streak=new_incorrect_streak,
            score_points=score_result.total_points,
            score_breakdown=score_result.breakdown,
            repetitions=new_card.reps,
            easiness_factor=new_card.stability,
            custom_state=new_card.state,
            precise_interval=new_card.difficulty
        )

        # 6. Apply to Progress (SKIP if Cramming + Already Knowing)
        should_update_schedule = True
        if is_cram and progress.status != 'new':
            should_update_schedule = False
            
        if should_update_schedule:
            progress.status = srs_result.status
            progress.interval = srs_result.interval_minutes
            progress.easiness_factor = srs_result.easiness_factor  # Legacy compatibility
            progress.repetitions = srs_result.repetitions
            progress.due_time = srs_result.next_review
            
            # === WRITE TO NATIVE FSRS COLUMNS (Primary) ===
            progress.fsrs_stability = new_card.stability
            progress.fsrs_difficulty = new_card.difficulty
            progress.fsrs_last_review = now
            
            # Map state string to int
            state_string_to_int = {
                'new': LearningProgress.FSRS_STATE_NEW,
                'learning': LearningProgress.FSRS_STATE_LEARNING,
                'review': LearningProgress.FSRS_STATE_REVIEW,
                're-learning': LearningProgress.FSRS_STATE_RELEARNING,
            }
            progress.fsrs_state = state_string_to_int.get(new_card.state, LearningProgress.FSRS_STATE_NEW)
            
            # === ALSO write to mode_data for backward compatibility (temporary) ===
            if progress.mode_data is None:
                progress.mode_data = {}
            progress.mode_data['custom_state'] = srs_result.custom_state
            progress.mode_data['fsrs_stability'] = new_card.stability
            progress.mode_data['fsrs_difficulty'] = new_card.difficulty
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(progress, 'mode_data')

        progress.correct_streak = srs_result.correct_streak
        progress.incorrect_streak = srs_result.incorrect_streak
        progress.last_reviewed = now
        # Store stability in legacy mastery column
        progress.mastery = srs_result.stability
        
        # Legacy counters
        if quality >= 4:
            progress.times_correct = (progress.times_correct or 0) + 1
        elif quality >= 2:
            progress.times_vague = (progress.times_vague or 0) + 1
        else:
            progress.times_incorrect = (progress.times_incorrect or 0) + 1
        
        # 7. Log Review
        log_entry = ReviewLog(
            user_id=user_id,
            item_id=item_id,
            timestamp=now,
            rating=quality,
            duration_ms=duration_ms,
            interval=progress.interval,
            easiness_factor=progress.easiness_factor,
            review_type=mode,
            mastery_snapshot=srs_result.stability,
            memory_power_snapshot=srs_result.retrievability,
            score_change=srs_result.score_points,
            is_correct=is_correct,
            session_id=session_id,
            container_id=container_id,
            mode=learning_mode or mode,
            streak_position=streak_position or srs_result.correct_streak
        )
        db.session.add(log_entry)
        
        return progress, srs_result
    
    # === Helper Methods ===

    @staticmethod
    def get_memory_power(progress: LearningProgress) -> float:
        """
        Calculate current Memory Power using FSRS-5 formula.
        
        Returns:
            Memory Power (0.0 - 1.0)
        """
        if not progress:
            return 0.0
        
        # Stability from easiness_factor
        stability = float(progress.easiness_factor) if progress.easiness_factor and progress.easiness_factor > 0 else 0.1
        
        # Mastery: M = 0.1 + 0.9 * (1 - exp(-0.03 * S))
        mastery = 0.1 + 0.9 * (1.0 - math.exp(-0.03 * stability))
        mastery = min(1.0, max(0.1, mastery))
        
        # Retention: R = 0.9^(t/S)
        if progress.last_reviewed and stability > 0:
            now = datetime.datetime.now(datetime.timezone.utc)
            last_review = progress.last_reviewed
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=datetime.timezone.utc)
            elapsed_days = (now - last_review).total_seconds() / 86400.0
            if elapsed_days > 0:
                retention = 0.9 ** (elapsed_days / stability)
            else:
                retention = 1.0
        else:
            retention = 1.0
        
        return mastery * retention

    # === Learning Interaction Processing ===

    @staticmethod
    def process_interaction(user_id: int, item_id: int, mode: str, result_data: dict):
        """
        Process a user's learning interaction.
        Orchestrates:
        1. Quality Normalization
        2. SRS Update (FSRS) via process_answer
        3. Gamification Points Awarding
        
        Returns: Dict summary
        """
        # 1. Normalize Result
        quality = FsrsService._normalize_quality(mode, result_data)

        # 2. Process Answer (SRS + ReviewLog + Score Calc)
        progress, srs_result = FsrsService.process_answer(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            duration_ms=result_data.get('duration_ms', 0),
        )
        
        # 3. Gamification Points
        from mindstack_app.modules.gamification.services.scoring_service import ScoreService
        
        # Calculate score points (redundant calc for verification, or just use srs_result.score_points)
        score_change = srs_result.score_points
        
        award_result = ScoreService.award_points(
            user_id=user_id,
            amount=score_change,
            reason=f"{mode.upper()} Answer (Quality: {quality})",
            item_id=item_id,
            item_type='VOCABULARY_ITEM'
        )
        
        updated_total_score = award_result.get('new_total', 0)
        
        # 4. Construct Response
        return {
            'quality': quality,
            'status': progress.status,
            'is_correct': quality >= 3,
            'next_review': progress.due_time.isoformat() if progress.due_time else None,
            'score_change': score_change,
            'points_breakdown': srs_result.score_breakdown, 
            'updated_total_score': updated_total_score,
            'memory_power': {
                'mastery': round(srs_result.stability, 2),  # Use Stability
                'retention': round(srs_result.retrievability * 100, 1),
                'memory_power': round(srs_result.retrievability * 100, 1), # Simplify MP=R
                'old_memory_power': 0, # Not tracking old for this flow currently
                'correct_streak': progress.correct_streak,
                'interval_minutes': progress.interval
            }
        }

    @staticmethod
    def calculate_retention_rate(last_reviewed: datetime.datetime, interval_minutes: int) -> int:
        """
        Calculate retention probability as percentage.
        """
        if not last_reviewed or interval_minutes <= 0:
            return 100
            
        now = datetime.datetime.now(datetime.timezone.utc)
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=datetime.timezone.utc)
            
        elapsed_days = (now - last_reviewed).total_seconds() / 86400.0
        stability = interval_minutes / 1440.0
        
        if stability <= 0:
            return 100
            
        retention = 0.9 ** (elapsed_days / stability)
        return int(retention * 100)

    # === Quality Normalization Helper ===
    
    @staticmethod
    def _normalize_quality(mode: str, result_data: dict) -> int:
        """Helper to map various inputs to FSRS Rating (1-4)."""
        # Explicit Quality
        if 'quality' in result_data:
            q = int(result_data['quality'])
            if q >= 5: return 4
            if q == 4: return 3
            if q == 3: return 2
            return 1

        # Boolean Correctness
        if 'is_correct' in result_data:
            return 3 if result_data['is_correct'] else 1
            
        # Accuracy (Typing/Listening)
        if 'accuracy' in result_data:
            acc = float(result_data['accuracy'])
            if acc >= 95: return 4
            if acc >= 85: return 3
            if acc >= 60: return 2
            return 1
            
        return 3 # Default to Good
    
    # === Batch Statistics Methods ===
    
    @staticmethod
    def get_item_stats(progress: LearningProgress) -> dict:
        """
        Get real-time statistics for a single item using FSRS.
        
        Args:
            progress: LearningProgress record
        
        Returns:
            Dict with mastery, retention, memory_power, is_due
        """
        if not progress:
            return {'mastery': 0, 'retention': 0, 'memory_power': 0, 'is_due': True}

        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Stability
        stability = float(progress.easiness_factor) if progress.easiness_factor and progress.easiness_factor > 0 else 0.1
        
        # Mastery: M = 0.1 + 0.9 * (1 - exp(-0.03 * S))
        mastery = 0.1 + 0.9 * (1.0 - math.exp(-0.03 * stability))
        mastery = min(1.0, max(0.1, mastery))
        
        # Retention: R = 0.9^(t/S)
        if progress.last_reviewed and stability > 0:
            last_review = progress.last_reviewed
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=datetime.timezone.utc)
            elapsed_days = (now - last_review).total_seconds() / 86400.0
            if elapsed_days > 0:
                retention = 0.9 ** (elapsed_days / stability)
            else:
                retention = 1.0
        else:
            retention = 1.0
            
        memory_power = mastery * retention
        
        if progress.due_time:
            due_aware = progress.due_time.replace(tzinfo=datetime.timezone.utc) if progress.due_time.tzinfo is None else progress.due_time
            is_due = now >= due_aware
        else:
            is_due = True
            
        return {
            'mastery': mastery,
            'retention': retention,
            'memory_power': memory_power,
            'is_due': is_due,
            'status': progress.status
        }
    
    @staticmethod
    def get_container_stats(user_id: int, container_id: int, mode: Optional[str] = None) -> dict:
        """
        Get aggregate statistics for a container (e.g., flashcard set).
        
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
        
        # Use local efficient batch calculation
        return FsrsService.calculate_batch_stats(progress_records)

    @staticmethod
    def calculate_batch_stats(
        progress_records: list,
        now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for multiple items efficiently.
        
        Used for dashboard analytics.
        
        Args:
            progress_records: List of LearningProgress objects
            now: Current time (default: now)
        
        Returns:
            Aggregate stats dictionary
        """
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        
        stats_list = []
        
        for progress in progress_records:
            # Stability from easiness_factor
            stability = float(progress.easiness_factor) if progress.easiness_factor and progress.easiness_factor > 0 else 0.1
            
            # Calculate mastery using FSRS formula: M = 0.1 + 0.9 * (1 - exp(-0.03 * S))
            mastery = 0.1 + 0.9 * (1.0 - math.exp(-0.03 * stability))
            mastery = min(1.0, max(0.1, mastery))
            
            # Calculate retention using FSRS formula: R = 0.9^(t/S)
            if progress.last_reviewed and stability > 0:
                last_review = progress.last_reviewed
                if last_review.tzinfo is None:
                    last_review = last_review.replace(tzinfo=datetime.timezone.utc)
                elapsed_days = (now - last_review).total_seconds() / 86400.0
                if elapsed_days > 0:
                    retention = 0.9 ** (elapsed_days / stability)
                else:
                    retention = 1.0
            else:
                retention = 1.0
            
            memory_power = mastery * retention
            
            # Fix: make due_time aware before comparison
            if progress.due_time:
                due_aware = progress.due_time.replace(tzinfo=datetime.timezone.utc) if progress.due_time.tzinfo is None else progress.due_time
                is_due = now >= due_aware
            else:
                is_due = True
            
            stats_list.append({
                'item_id': progress.item_id,
                'memory_power': memory_power,
                'mastery': mastery,
                'retention': retention,
                'is_due': is_due
            })
        
        # Aggregate
        total_items = len(stats_list)
        if total_items == 0:
            return {
                'total_items': 0,
                'average_memory_power': 0,
                'strong_items': 0,
                'medium_items': 0,
                'weak_items': 0,
                'due_items': 0
            }
        
        avg_mp = sum(s['memory_power'] for s in stats_list) / total_items
        strong = len([s for s in stats_list if s['memory_power'] >= 0.8])
        medium = len([s for s in stats_list if 0.5 <= s['memory_power'] < 0.8])
        weak = len([s for s in stats_list if s['memory_power'] < 0.5])
        due = len([s for s in stats_list if s['is_due']])
        
        return {
            'total_items': total_items,
            'average_memory_power': round(avg_mp, 4),
            'strong_items': strong,  # 80-100%
            'medium_items': medium,  # 50-80%
            'weak_items': weak,  # 0-50%
            'due_items': due
        }


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
        # Ensure avg_memory_power is scaled to 0-100 for charting
        review_dict = {}
        for r in reviews:
            val = float(r.avg_memory_power) if r.avg_memory_power else 0
            # If stored as decimal, multiply by 100
            if val <= 1.05:
                review_dict[r.review_date] = round(val * 100, 1)
            else:
                review_dict[r.review_date] = round(val, 1)
        
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
            # Standardize snapshot (Legacy bug fix: ensure it's 0-100 for UI but check if stored as 0-1)
            mp_snap = review.memory_power_snapshot or 0.0
            if mp_snap <= 1.05: # Stored as decimal (0-1)
                mp_display = round(mp_snap * 100, 1)
            else: # Stored as percentage (Legacy bug)
                mp_display = round(mp_snap, 1)

            history.append({
                'timestamp': review.timestamp.isoformat(),
                'date': review.timestamp.strftime('%Y-%m-%d %H:%M'),
                'rating': review.rating,
                'memory_power': mp_display,
                'interval': review.interval,
                'ease_factor': review.easiness_factor
            })
        
        return history

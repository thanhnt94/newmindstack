"""
HybridFSRSEngine (Standard FSRS-5 via fsrs-rs-python)

Core: FSRS-5 (Rust via fsrs-rs-python)
Standard 4-button system: Again(1), Hard(2), Good(3), Easy(4)
Safety Caps: 20m min, 365d max
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from fsrs_rs_python import FSRS, DEFAULT_PARAMETERS

# Standard FSRS Rating (1-4)
class Rating:
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

@dataclass
class CardState:
    """
    Local DTO to bridge between Database (LearningProgress) and FSRS Library.
    """
    stability: float = 0.0      # FSRS S (stored in easiness_factor column)
    difficulty: float = 0.0     # FSRS D (stored in precise_interval column)
    elapsed_days: float = 0.0
    scheduled_days: float = 0   # Interval in days
    reps: int = 0
    lapses: int = 0
    state: str = 'new'          # new, learning, review, re-learning
    last_review: Optional[datetime] = None
    due: Optional[datetime] = None

class HybridFSRSEngine:
    """
    Standard FSRS-5 Engine using fsrs-rs-python.
    
    Features:
    - Pure FSRS-5 algorithm (no custom multipliers)
    - 4-button rating: Again(1), Hard(2), Good(3), Easy(4)
    - Safety caps: Floor 20 min, Ceiling 365 days
    - User-specific parameters support
    """
    
    def __init__(self, custom_weights: Optional[List[float]] = None, desired_retention: float = 0.9):
        """
        Initialize the FSRS engine.
        
        Args:
            custom_weights: Optional 19 floats from FSRS optimizer.
            desired_retention: Target retention rate (0.7 - 0.99).
        """
        params = custom_weights if custom_weights else list(DEFAULT_PARAMETERS)
        self.fsrs = FSRS(parameters=params)
        self.desired_retention = desired_retention

    def _to_memory_state(self, state: CardState):
        """Convert local CardState to fsrs-rs MemoryState (or None for new card)."""
        if state.state == 'new' or (state.stability <= 0 and state.reps == 0):
            return None
        
        try:
            from fsrs_rs_python import MemoryState
            return MemoryState(
                stability=max(0.1, float(state.stability)),
                difficulty=max(1.0, min(10.0, float(state.difficulty)))
            )
        except ImportError:
            return (max(0.1, float(state.stability)), max(1.0, min(10.0, float(state.difficulty))))

    def _from_next_state(self, item_state, card_state: CardState, rating: int) -> CardState:
        """Convert fsrs-rs ItemState to local CardState."""
        memory = item_state.memory
        interval = item_state.interval
        
        # Determine state based on rating and reps
        if rating == Rating.Again:
            if card_state.reps == 0:
                new_state = 'learning'
            else:
                new_state = 're-learning'
            new_lapses = card_state.lapses + 1
        else:
            if card_state.reps == 0:
                new_state = 'learning'
            else:
                new_state = 'review'
            new_lapses = card_state.lapses
        
        return CardState(
            stability=memory.stability,
            difficulty=memory.difficulty,
            elapsed_days=0.0,
            scheduled_days=float(interval),
            reps=card_state.reps + 1,
            lapses=new_lapses,
            state=new_state,
            last_review=card_state.last_review,
            due=card_state.due
        )

    def get_realtime_retention(self, card_state: CardState, now: datetime) -> float:
        """
        Calculate real-time retrievability.
        
        Formula: R = 0.9^(t/S) where t = elapsed days, S = stability
        
        Returns: Float 0.0 - 1.0
        """
        if card_state.state == 'new' or card_state.stability <= 0:
            return 1.0
            
        if not card_state.last_review:
            return 1.0
            
        last_review = card_state.last_review
        if last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
            
        elapsed = (now - last_review).total_seconds() / 86400.0
        if elapsed <= 0:
            return 1.0
            
        try:
            return 0.9 ** (elapsed / card_state.stability)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def review_card(self, card_state: CardState, rating: int, now: Optional[datetime] = None) -> Tuple[CardState, datetime, Dict[str, Any]]:
        """
        Process review with standard FSRS-5 algorithm.
        
        Args:
            card_state: Current card state
            rating: FSRS rating 1-4 (Again/Hard/Good/Easy)
            now: Review timestamp
            
        Returns:
            (new_card_state, due_datetime, log_dict)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Clamp rating to valid range
        fsrs_rating = max(1, min(4, rating))
        
        # Get current memory state
        memory_state = self._to_memory_state(card_state)
        r_before = self.get_realtime_retention(card_state, now)
        
        # Calculate days elapsed since last review
        if card_state.last_review:
            last_review = card_state.last_review
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=timezone.utc)
            days_elapsed = (now - last_review).total_seconds() / 86400.0
        else:
            days_elapsed = 0.0
        
        # FSRS-5 calculation
        next_states = self.fsrs.next_states(
            memory_state,
            self.desired_retention,
            int(days_elapsed)
        )
        
        # Select state based on rating
        rating_map = {
            Rating.Again: next_states.again,
            Rating.Hard: next_states.hard,
            Rating.Good: next_states.good,
            Rating.Easy: next_states.easy
        }
        selected_state = rating_map[fsrs_rating]
        
        # Get raw interval
        raw_interval = float(selected_state.interval)
        
        # Apply safety caps (no custom multipliers)
        FLOOR_DAYS = 20.0 / 1440.0  # 20 minutes
        CEILING_DAYS = 365.0
        
        final_interval = raw_interval
        if final_interval < FLOOR_DAYS:
            final_interval = FLOOR_DAYS
        elif final_interval > CEILING_DAYS:
            final_interval = CEILING_DAYS
            
        # Build result CardState
        new_card_state = self._from_next_state(selected_state, card_state, fsrs_rating)
        new_card_state.scheduled_days = final_interval
        new_card_state.last_review = now
        new_card_state.due = now + timedelta(days=final_interval)
        
        # Log for debugging
        log = {
            "rating": fsrs_rating,
            "raw_fsrs_days": raw_interval,
            "final_days": final_interval,
            "stability": new_card_state.stability,
            "difficulty": new_card_state.difficulty,
            "retention_at_review": r_before,
            "state": new_card_state.state
        }
        
        return new_card_state, new_card_state.due, log

    def preview_intervals(self, card_state: CardState, now: Optional[datetime] = None) -> Dict[int, float]:
        """
        Preview intervals for all 4 ratings without modifying state.
        
        Returns: {1: again_days, 2: hard_days, 3: good_days, 4: easy_days}
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
            
        memory_state = self._to_memory_state(card_state)
        
        if card_state.last_review:
            last_review = card_state.last_review
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=timezone.utc)
            days_elapsed = (now - last_review).total_seconds() / 86400.0
        else:
            days_elapsed = 0.0
        
        next_states = self.fsrs.next_states(
            memory_state,
            self.desired_retention,
            int(days_elapsed)
        )
        
        return {
            Rating.Again: float(next_states.again.interval),
            Rating.Hard: float(next_states.hard.interval),
            Rating.Good: float(next_states.good.interval),
            Rating.Easy: float(next_states.easy.interval)
        }

# Alias for compatibility
FSRSEngineV5 = HybridFSRSEngine

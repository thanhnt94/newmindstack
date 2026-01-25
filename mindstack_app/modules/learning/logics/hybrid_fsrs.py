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

# FSRS Math State Constants
STATE_NEW = 0
STATE_LEARNING = 1
STATE_REVIEW = 2
STATE_RELEARNING = 3

@dataclass
class CardState:
    """
    DTO bridging Database (LearningProgress) and FSRS Library.
    
    Maps directly to LearningProgress native columns:
    - stability -> fsrs_stability
    - difficulty -> fsrs_difficulty
    - state -> fsrs_state (Integer: 0-3)
    """
    stability: float = 0.0      # FSRS S (days)
    difficulty: float = 0.0     # FSRS D (1-10) - Default 0.0 for new
    elapsed_days: float = 0.0
    scheduled_days: float = 0   # Interval in days
    reps: int = 0
    lapses: int = 0             # Count of forgetful events from mature state
    state: int = STATE_NEW      # 0=New, 1=Learning, 2=Review, 3=Relearning
    last_review: Optional[datetime] = None
    due: Optional[datetime] = None

class HybridFSRSEngine:
    """
    Standard FSRS-5 Engine using fsrs-rs-python.
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
        # If state is New (0) or stability is 0/None, treat as new
        if state.state == STATE_NEW or (state.stability <= 0 and state.reps == 0):
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
        """
        Convert fsrs-rs ItemState to local CardState.
        
        [REFACTORED] State transition now based on interval (scheduled_days) per Native FSRS v5:
        - interval >= 1.0 day: STATE_REVIEW (Graduated to Review)
        - interval < 1.0 day: STATE_LEARNING or STATE_RELEARNING (Short-term memory)
        
        This eliminates "Learning Hell" where users get stuck in Learning state.
        """
        memory = item_state.memory
        interval = float(item_state.interval)
        
        # ============================================================
        # 1. NATIVE FSRS STATE TRANSITION (Interval-Based)
        # ============================================================
        # Core principle: The INTERVAL determines cognitive state, not the button pressed.
        # - Long interval (>= 1 day) = Memory is stable enough for spaced review
        # - Short interval (< 1 day) = Still in active learning/relearning phase
        
        GRADUATION_THRESHOLD_DAYS = 1.0  # >= 1 day = Review state
        
        if interval >= GRADUATION_THRESHOLD_DAYS:
            # Long-term memory: Card graduates to Review state
            new_state = STATE_REVIEW
        else:
            # Short-term memory: Determine based on lapse history
            if rating == Rating.Again:
                # User forgot - check if this is a lapse from mature state
                if card_state.state == STATE_REVIEW:
                    new_state = STATE_RELEARNING  # Review -> Relearning (Lapse)
                elif card_state.state == STATE_RELEARNING:
                    new_state = STATE_RELEARNING  # Stay in Relearning
                else:
                    new_state = STATE_LEARNING    # New/Learning -> Stay in Learning
            else:
                # User remembered but interval is still short
                # Preserve the "relearning" vs "learning" distinction
                if card_state.state == STATE_RELEARNING:
                    new_state = STATE_RELEARNING  # Stay in Relearning until graduation
                elif card_state.state == STATE_REVIEW:
                    # Edge case: Review with very short interval (shouldn't happen normally)
                    new_state = STATE_REVIEW
                else:
                    new_state = STATE_LEARNING    # New/Learning -> Stay in Learning
        
        # ============================================================
        # 2. LAPSE COUNTING
        # ============================================================
        # A lapse occurs when a MATURE card (Review state) is forgotten.
        # Relearning cards that are forgotten again don't increment lapses
        # (they're already counted as lapsed).
        
        new_lapses = card_state.lapses
        if rating == Rating.Again and card_state.state == STATE_REVIEW:
            new_lapses += 1
        
        return CardState(
            stability=memory.stability,
            difficulty=memory.difficulty,
            elapsed_days=0.0,
            scheduled_days=interval,
            reps=card_state.reps + 1,
            lapses=new_lapses,
            state=new_state,
            last_review=card_state.last_review,
            due=card_state.due
        )

    def get_realtime_retention(self, card_state: CardState, now: datetime) -> float:
        """
        Calculate real-time retrievability.
        Formula: R = 0.9^(t/S)
        """
        if card_state.state == STATE_NEW or card_state.stability <= 0:
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

    def review_card(self, card_state: CardState, rating: int, now: Optional[datetime] = None, enable_fuzz: bool = False) -> Tuple[CardState, datetime, Dict[str, Any]]:
        """
        Process review with standard FSRS-5 algorithm.
        Returns: (new_card_state, due_datetime, log_dict)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Clamp rating 1-4
        fsrs_rating = max(1, min(4, rating))
        
        memory_state = self._to_memory_state(card_state)
        r_before = self.get_realtime_retention(card_state, now)
        
        # Elapsed days
        if card_state.last_review:
            last_review = card_state.last_review
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=timezone.utc)
            days_elapsed = (now - last_review).total_seconds() / 86400.0
        else:
            days_elapsed = 0.0
        
        days_elapsed_rounded = max(0, round(days_elapsed))
        next_states = self.fsrs.next_states(
            memory_state,
            self.desired_retention,
            days_elapsed_rounded
        )
        
        rating_map = {
            Rating.Again: next_states.again,
            Rating.Hard: next_states.hard,
            Rating.Good: next_states.good,
            Rating.Easy: next_states.easy
        }
        selected_state = rating_map[fsrs_rating]
        
        raw_interval = float(selected_state.interval)
        
        # Apply Caps
        FLOOR_DAYS = 20.0 / 1440.0  # 20 minutes
        CEILING_DAYS = 365.0
        
        final_interval = raw_interval
        if final_interval < FLOOR_DAYS:
            final_interval = FLOOR_DAYS
        elif final_interval > CEILING_DAYS:
            final_interval = CEILING_DAYS
            
        # Build Result
        new_card_state = self._from_next_state(selected_state, card_state, fsrs_rating)
        
        # 3. Apply Fuzzing (Interval Randomization)
        # Threshold and range from MemoryPowerConfigService (or defaults)
        # We use a random.uniform(0.95, 1.05) to apply +/- 5% variance.
        fuzzed_interval = final_interval
        if enable_fuzz and final_interval > 3.0: # Default threshold
             import random as py_random
             fuzz_factor = py_random.uniform(0.95, 1.05)
             fuzzed_interval = final_interval * fuzz_factor
             # Ensure we don't fuzz below the threshold
             fuzzed_interval = max(3.0, fuzzed_interval)
        
        new_card_state.scheduled_days = fuzzed_interval
        new_card_state.last_review = now
        new_card_state.due = now + timedelta(days=fuzzed_interval)
        
        log = {
            "rating": fsrs_rating,
            "days_elapsed": days_elapsed,
            "scheduled_days": fuzzed_interval,
            "review_duration": 0, # Placeholder, caller should fill
            "start_state": card_state.state,
            "end_state": new_card_state.state,
            "original_interval": final_interval
        }
        
        return new_card_state, new_card_state.due, log

    def preview_intervals(self, card_state: CardState, now: Optional[datetime] = None) -> Dict[int, float]:
        """
        Preview intervals for all 4 ratings without modifying state.
        [DEPRECATED] Use preview_states for more data.
        """
        states = self.preview_states(card_state, now)
        return {r: states[r]['interval'] for r in states}

    def preview_states(self, card_state: CardState, now: Optional[datetime] = None) -> Dict[int, Dict[str, float]]:
        """
        Preview full next states (Stability, Difficulty, Interval) for all ratings.
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
        
        days_elapsed_rounded = max(0, round(days_elapsed))
        next_states = self.fsrs.next_states(
            memory_state,
            self.desired_retention,
            days_elapsed_rounded
        )
        
        rating_map = {
            Rating.Again: next_states.again,
            Rating.Hard: next_states.hard,
            Rating.Good: next_states.good,
            Rating.Easy: next_states.easy
        }

        result = {}
        for r, ns in rating_map.items():
            result[r] = {
                'stability': float(ns.memory.stability),
                'difficulty': float(ns.memory.difficulty),
                'interval': float(ns.interval)
            }
        return result

# Alias
FSRSEngineV5 = HybridFSRSEngine

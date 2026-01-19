"""
SRS Engine - Strict Custom Spaced Repetition System (Spec v7)

This module implements a complete, custom SRS algorithm with:
1. INPUT NORMALIZATION: Maps 3/4/6 button systems to Quality 0-5.
2. STATE MACHINE: NEW (Minutes), LEARNED (Days), HARD (Days), MASTER (Days).
3. SAFETY VALVE: NEW state cards that don't graduate after 10 reps go to HARD.
4. REVIEW AHEAD: Uses elapsed_time if user reviews early.
5. RETENTION CURVE: R = R0 × (0.9)^(Elapsed/Interval) with R0 per score.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# PART 1: INPUT NORMALIZATION
# ============================================================================

class InputNormalizer:
    """
    Maps user input from different UI layouts to a standard Quality Score (0-5).
    
    6-Button: 0, 1, 2, 3, 4, 5.
    4-Button: 0 (Fail), 2 (Hard), 4 (MCQ Correct), 5 (Typing Correct).
    3-Button: 0 (Fail), 3 (Pass), 5 (Easy).
    """
    
    MAPPINGS = {
        6: {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5},
        4: {0: 0, 1: 2, 2: 4, 3: 5},
        3: {0: 0, 1: 3, 2: 5}
    }
    
    @staticmethod
    def normalize(raw_input: int, button_count: int = 6) -> int:
        """Normalize raw button input to Quality 0-5."""
        mapping = InputNormalizer.MAPPINGS.get(button_count, InputNormalizer.MAPPINGS[6])
        return mapping.get(raw_input, 0)


# ============================================================================
# PART 2: CONSTANTS & ENUMS
# ============================================================================

class SRSState(str, Enum):
    """Card states in the SRS system."""
    NEW = 'new'
    LEARNED = 'learned'
    HARD = 'hard'
    MASTER = 'master'


# Initial Retention (R0) by Score (for UI display)
INIT_RETENTION_MAP = {
    0: 0.20,   # 20%
    1: 0.40,   # 40%
    2: 0.70,   # 70%
    3: 0.85,   # 85%
    4: 0.95,   # 95%
    5: 1.00    # 100%
}

# Thresholds
NEW_GRADUATION_THRESHOLD_MINUTES = 2880.0  # 2 days in minutes
NEW_SAFETY_VALVE_REPS = 10                  # Max reps in NEW before forcing HARD
STREAK_TO_MASTER = 10                       # Streak to promote to MASTER
HARD_STREAK_TO_EXIT = 3                     # Hard streak to return to LEARNED

# Formulas as lambdas (Input: current value, Output: next value)
SRS_FORMULAS = {
    'new': {
        0: lambda x: 10.0,                    # Hard Reset to 10 minutes.
        1: lambda x: max(10.0, x * 0.5),      # Soft Reset.
        2: lambda x: x * 1.1,                 # Struggle / Tiny Step.
        3: lambda x: x * 1.5,                 # Slow Progress.
        4: lambda x: x * 2.5,                 # Standard Progress.
        5: lambda x: x * 4.0                  # Fast Track.
    },
    'learned': {
        0: lambda x: 1.0,                     # Hard Reset to 1 day -> HARD.
        1: lambda x: max(1.5, x * 0.5),       # Soft Reset -> HARD.
        2: lambda x: x * 1.2,                 # Minimal growth.
        3: lambda x: x * 1.8,                 # Moderate growth.
        4: lambda x: x * 2.5,                 # Strong growth.
        5: lambda x: x * 3.5                  # Very strong growth.
    },
    'hard': {
        0: lambda x: 1.0,                     # Hard Reset.
        1: lambda x: max(1.5, x * 0.5),       # Soft Reset.
        2: lambda x: x * 1.0,                 # Stagnation (punishment).
        3: lambda x: x * 1.15,                # Tiny growth.
        4: lambda x: x * 1.3,                 # Small growth.
        5: lambda x: x * 1.5                  # Medium growth.
    },
    'master': {
        # 0, 1 -> Drop to HARD (use learned fail formulas)
        2: lambda x: x * 1.56,                # 1.2 * 1.3
        3: lambda x: x * 2.34,                # 1.8 * 1.3
        4: lambda x: x * 3.25,                # 2.5 * 1.3
        5: lambda x: x * 4.55                 # 3.5 * 1.3
    }
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CardState:
    """Complete state of a card in the SRS system."""
    state: str = SRSState.NEW.value      # new, learned, hard, master
    interval: float = 10.0                # Minutes for NEW, Days for others
    correct_streak: int = 0
    hard_streak: int = 0
    new_state_reps: int = 0               # Safety valve counter
    last_reviewed: Optional[datetime] = None


@dataclass 
class SRSResult:
    """Result of processing an answer."""
    next_interval: float                  # Minutes for NEW, Days for others
    next_state: str
    retention_percent: float              # R0 value for this score
    review_log: Dict[str, Any]            # Debug/audit log


# ============================================================================
# SRS ENGINE (Spec v7)
# ============================================================================

class SRSEngine:
    """
    Strict Custom SRS Engine (Spec v7).
    
    Features:
    - 4-state machine: NEW, LEARNED, HARD, MASTER.
    - Safety valve: NEW cards that don't graduate after 10 reps go to HARD.
    - Review Ahead: Uses elapsed_time if user reviews early.
    - Retention Curve: R = R0 × (0.9)^(Elapsed/Interval).
    """

    # === INPUT NORMALIZATION ===
    
    @staticmethod
    def normalize_quality(raw_input: int, button_count: int = 6) -> int:
        """Map raw button input to Quality 0-5."""
        return InputNormalizer.normalize(raw_input, button_count)

    # === RETENTION CURVE ===
    
    @staticmethod
    def calculate_retention(
        r0: float,
        elapsed_time: float,
        scheduled_interval: float
    ) -> float:
        """
        Calculate retention percentage.
        
        Formula: R = R0 × (0.9)^(Elapsed / Interval)
        
        Args:
            r0: Initial retention (0.0-1.0).
            elapsed_time: Time since last review.
            scheduled_interval: Scheduled interval (same units).
            
        Returns:
            Retention percentage (0.0-1.0).
        """
        if scheduled_interval <= 0:
            return r0
        
        ratio = elapsed_time / scheduled_interval
        retention = r0 * (0.9 ** ratio)
        return max(0.0, min(1.0, retention))

    # === MAIN ALGORITHM ===
    
    @staticmethod
    def process_answer(
        card: CardState,
        quality: int,
        now: Optional[datetime] = None
    ) -> SRSResult:
        """
        Process user answer using Spec v7 logic.
        
        Args:
            card: Current CardState.
            quality: Normalized Quality Score (0-5).
            now: Current timestamp (UTC).
            
        Returns:
            SRSResult with next_interval, next_state, retention, log.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # --- Initialize ---
        state = card.state
        interval = card.interval
        correct_streak = card.correct_streak
        hard_streak = card.hard_streak
        new_state_reps = card.new_state_reps
        
        # Get R0 for this score
        r0 = INIT_RETENTION_MAP.get(quality, 1.0)
        
        # Calculate elapsed time for Review Ahead logic
        elapsed_minutes = 0.0
        if card.last_reviewed:
            elapsed_minutes = (now - card.last_reviewed).total_seconds() / 60.0
        elapsed_days = elapsed_minutes / 1440.0
        
        # Review log
        log = {
            'prev_state': state,
            'prev_interval': interval,
            'quality': quality,
            'elapsed_minutes': elapsed_minutes,
            'transition': None
        }
        
        # === STATE MACHINE ===
        
        # --- A. STATE: NEW (Minutes) ---
        if state == SRSState.NEW.value:
            current_val = interval
            
            # Apply formula
            formula = SRS_FORMULAS['new'].get(quality, SRS_FORMULAS['new'][0])
            next_interval = formula(current_val)
            
            # Safety Valve: If too many reps in NEW without graduating
            new_state_reps += 1
            if new_state_reps >= NEW_SAFETY_VALVE_REPS and next_interval <= NEW_GRADUATION_THRESHOLD_MINUTES:
                # Force to HARD
                state = SRSState.HARD.value
                interval = 1.0  # 1 day
                correct_streak = 0
                new_state_reps = 0
                log['transition'] = 'NEW -> HARD (Safety Valve)'
            
            elif next_interval > NEW_GRADUATION_THRESHOLD_MINUTES:
                # Graduate to LEARNED
                state = SRSState.LEARNED.value
                interval = next_interval / 1440.0  # Convert to days
                correct_streak = 0
                new_state_reps = 0
                log['transition'] = 'NEW -> LEARNED (Graduation)'
            else:
                # Stay in NEW
                interval = next_interval
            
            # Update streak
            if quality >= 3:
                correct_streak += 1
            else:
                correct_streak = 0
        
        # --- B/C/D. STATES: LEARNED / HARD / MASTER (Days) ---
        else:
            current_days = interval
            
            # REVIEW AHEAD LOGIC (Part 3)
            # If reviewed early, use elapsed_time as base instead of scheduled.
            base_for_calc = current_days
            if elapsed_days > 0 and elapsed_days < current_days:
                base_for_calc = elapsed_days
                log['review_ahead'] = True
            
            next_days = current_days  # Placeholder
            
            # --- C. STATE: HARD ---
            if state == SRSState.HARD.value:
                formula_h = SRS_FORMULAS['hard'].get(quality, SRS_FORMULAS['hard'][0])
                next_days = formula_h(base_for_calc)
                
                if quality >= 4:
                    hard_streak += 1
                elif quality < 2:
                    hard_streak = 0
                
                # Exit to LEARNED if streak >= 3
                if hard_streak >= HARD_STREAK_TO_EXIT:
                    state = SRSState.LEARNED.value
                    hard_streak = 0
                    correct_streak = 0
                    log['transition'] = 'HARD -> LEARNED (Exit)'
                
                interval = next_days
            
            # --- D. STATE: MASTER ---
            elif state == SRSState.MASTER.value:
                if quality <= 1:
                    # Failure: Drop to HARD
                    state = SRSState.HARD.value
                    formula_fail = SRS_FORMULAS['learned'].get(quality)
                    next_days = formula_fail(base_for_calc)
                    correct_streak = 0
                    hard_streak = 0
                    log['transition'] = 'MASTER -> HARD (Failure)'
                else:
                    # Success: Apply MASTER bonus
                    formula_m = SRS_FORMULAS['master'].get(quality)
                    if formula_m:
                        next_days = formula_m(base_for_calc)
                    else:
                        next_days = base_for_calc * 1.3
                    
                    if quality >= 4:
                        correct_streak += 1
                
                interval = next_days
            
            # --- B. STATE: LEARNED ---
            else:
                if quality <= 1:
                    # Failure: Move to HARD
                    state = SRSState.HARD.value
                    formula_fail = SRS_FORMULAS['learned'].get(quality)
                    next_days = formula_fail(base_for_calc)
                    correct_streak = 0
                    hard_streak = 0
                    log['transition'] = 'LEARNED -> HARD (Failure)'
                else:
                    # Success
                    formula_l = SRS_FORMULAS['learned'].get(quality)
                    next_days = formula_l(base_for_calc)
                    
                    if quality >= 4:
                        correct_streak += 1
                    
                    # Promotion to MASTER
                    if correct_streak >= STREAK_TO_MASTER:
                        state = SRSState.MASTER.value
                        log['transition'] = 'LEARNED -> MASTER (Promotion)'
                
                interval = next_days
        
        # === FINALIZE ===
        
        # Ensure minimum interval
        if state == SRSState.NEW.value:
            interval = max(10.0, interval)  # Min 10 minutes
        else:
            interval = max(0.5, interval)   # Min 0.5 days (12 hours)
        
        # Update card state (for return)
        log['next_state'] = state
        log['next_interval'] = interval
        
        return SRSResult(
            next_interval=round(interval, 4),
            next_state=state,
            retention_percent=round(r0 * 100, 1),
            review_log=log
        )

    # === UTILITY: Convert interval to due time ===
    
    @staticmethod
    def calculate_due_time(
        current_state: str,
        interval: float,
        now: Optional[datetime] = None
    ) -> datetime:
        """Calculate due time from interval."""
        if now is None:
            now = datetime.now(timezone.utc)
        
        if current_state == SRSState.NEW.value:
            # Interval is in minutes
            return now + timedelta(minutes=interval)
        else:
            # Interval is in days
            return now + timedelta(days=interval)


# ============================================================================
# COMPATIBILITY: Wrapper for existing MemoryEngine interface
# ============================================================================

class MemoryEngine:
    """
    Wrapper to maintain compatibility with existing code.
    Delegates to SRSEngine for core logic.
    """
    
    @staticmethod
    def calculate_retention(
        last_reviewed: Optional[datetime],
        interval: int,
        now: Optional[datetime] = None
    ) -> float:
        """Calculate retention using forgetting curve."""
        if last_reviewed is None:
            return 1.0
        
        if now is None:
            now = datetime.now(timezone.utc)
        
        # Ensure timezone
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        elapsed = (now - last_reviewed).total_seconds() / 60.0
        stability = max(interval, 1)
        
        # R = e^(-0.105 * elapsed / stability)
        decay_rate = 0.105 / stability
        retention = math.exp(-decay_rate * elapsed)
        
        return round(max(0.0, min(1.0, retention)), 4)
    
    @staticmethod
    def calculate_mastery(
        status: str,
        repetitions: int,
        correct_streak: int,
        incorrect_streak: int = 0
    ) -> float:
        """Calculate mastery (0.0-1.0) based on status and streaks."""
        if status == 'new':
            return 0.0
        
        if status == 'learning':
            base = 0.10 + min(repetitions, 7) * 0.06
            streak_bonus = max(0, (correct_streak - 3)) * 0.01
            return min(0.52, base + streak_bonus)
        
        if status in ('reviewing', 'mastered'):
            base = 0.60 + min(repetitions, 7) * 0.057
            streak_bonus = max(0, (correct_streak - 5)) * 0.02
            return min(1.0, base + streak_bonus)
        
        return 0.0
    
    @staticmethod
    def calculate_memory_power(mastery: float, retention: float) -> float:
        """Memory Power = Mastery × Retention."""
        return round(mastery * retention, 4)

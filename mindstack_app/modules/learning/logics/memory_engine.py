"""
Memory Power Engine - Custom SRS System (Spec v8)

5-State Machine: NEW → LEARNING → REVIEW ↔ HARD → MASTER
Scoring: 0-7 (Flashcard 0-5, MCQ 6, Typing 7)

Key Features:
- LEARNING: Minutes, Floor 20m, Graduation > 2880m (2 days)
- REVIEW: Days, Ceiling 365 days, Streak >= 10 → MASTER
- HARD: Penalty phase, Hard_Streak >= 3 → REVIEW
- MASTER: 1.2x Bonus, Soft Demotion (não HARD, về REVIEW với 50%)
- Safety Valve: LEARNING reps >= 10 → HARD
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# CONSTANTS
# ============================================================================

class CustomState(str, Enum):
    """Card states in the SRS system."""
    NEW = 'new'
    LEARNING = 'learning'
    REVIEW = 'review'
    HARD = 'hard'
    MASTER = 'master'


# Learning phase constants
LEARNING_FLOOR_MINUTES = 20.0
LEARNING_GRADUATION_THRESHOLD = 2880.0  # 2 days in minutes
LEARNING_SAFETY_VALVE_REPS = 10

# Review phase constants
REVIEW_CEILING_DAYS = 365.0
STREAK_TO_MASTER = 10
HARD_STREAK_TO_EXIT = 3

# Formulas for LEARNING state (Minutes)
LEARNING_FORMULAS = {
    0: lambda x: LEARNING_FLOOR_MINUTES,                    # Quên: Về sàn
    1: lambda x: max(LEARNING_FLOOR_MINUTES, x * 0.5),      # Sai: -50%
    2: lambda x: max(LEARNING_FLOOR_MINUTES, x * 0.8),      # Khó: -20% (PHẠT)
    3: lambda x: max(LEARNING_FLOOR_MINUTES, x * 1.5),      # Tạm
    4: lambda x: max(LEARNING_FLOOR_MINUTES, x * 2.5),      # Tốt
    5: lambda x: max(LEARNING_FLOOR_MINUTES, x * 4.0),      # Dễ
    6: lambda x: max(LEARNING_FLOOR_MINUTES, x * 5.0),      # MCQ
    7: lambda x: max(LEARNING_FLOOR_MINUTES, x * 7.0),      # Typing
}

# Formulas for REVIEW state (Days - Multipliers)
REVIEW_MULTIPLIERS = {
    # 0, 1: Fail → HARD
    2: 0.8,   # Khó: PHẠT -20%
    3: 1.8,   # Pass
    4: 2.5,   # Good
    5: 3.5,   # Easy
    6: 4.5,   # MCQ
    7: 6.0,   # Typing
}

# Formulas for HARD state (Days)
HARD_FORMULAS = {
    0: lambda x: 1.0,                   # Sai: Reset 1 day, Reset streak
    1: lambda x: 1.0,                   # Sai: Reset 1 day, Reset streak
    2: lambda x: max(1.0, x * 0.8),     # Khó: -20%, Reset streak
    3: lambda x: x * 1.2,               # Tạm: Keep streak
    4: lambda x: x * 1.3,               # Tốt: +1 streak
    5: lambda x: x * 1.3,               # Dễ: +1 streak
    6: lambda x: x * 1.4,               # MCQ: +1 streak
    7: lambda x: x * 1.5,               # Typing: +1 streak
}

# MASTER uses REVIEW multipliers * 1.2 bonus


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ProgressState:
    """Represents the state of a learning item."""
    status: str  # Legacy: 'new', 'learning', 'reviewing'
    mastery: float  # 0.0 - 1.0
    repetitions: int
    interval: int  # minutes
    correct_streak: int
    incorrect_streak: int
    easiness_factor: float
    
    # Spec v8 fields
    custom_state: str = CustomState.NEW.value
    hard_streak: int = 0
    learning_reps: int = 0  # Safety valve counter
    precise_interval: float = 20.0  # Float for precision


@dataclass
class AnswerResult:
    """Result of processing an answer."""
    new_state: ProgressState
    memory_power: float
    retention_percent: float


# ============================================================================
# MEMORY ENGINE (Spec v8)
# ============================================================================

class MemoryEngine:
    """
    Custom SRS Engine (Spec v8) with 5-State Machine.
    
    States: NEW → LEARNING → REVIEW ↔ HARD → MASTER
    Scoring: 0-7
    """

    # === RETENTION CURVE ===
    
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
        
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        elapsed = (now - last_reviewed).total_seconds() / 60.0
        stability = max(interval, 1)
        
        decay_rate = 0.105 / stability
        retention = math.exp(-decay_rate * elapsed)
        
        return round(max(0.0, min(1.0, retention)), 4)

    # === MASTERY CALCULATION ===
    
    @staticmethod
    def calculate_mastery(
        custom_state: str,
        repetitions: int,
        correct_streak: int
    ) -> float:
        """Calculate mastery (0.0-1.0) based on state and streaks."""
        if custom_state == CustomState.NEW.value:
            return 0.0
        
        if custom_state == CustomState.LEARNING.value:
            base = 0.10 + min(repetitions, 7) * 0.06
            streak_bonus = max(0, (correct_streak - 3)) * 0.01
            return min(0.52, base + streak_bonus)
        
        if custom_state == CustomState.HARD.value:
            return 0.30 + min(repetitions, 5) * 0.04
        
        if custom_state in (CustomState.REVIEW.value, CustomState.MASTER.value):
            base = 0.60 + min(repetitions, 7) * 0.057
            streak_bonus = max(0, (correct_streak - 5)) * 0.02
            if custom_state == CustomState.MASTER.value:
                base = min(1.0, base * 1.1)  # Master bonus
            return min(1.0, base + streak_bonus)
        
        return 0.0

    # === MEMORY POWER ===
    
    @staticmethod
    def calculate_memory_power(mastery: float, retention: float) -> float:
        """Memory Power = Mastery × Retention."""
        return round(mastery * retention, 4)

    # === MAIN ALGORITHM (Spec v8) ===
    
    @staticmethod
    def process_answer(
        current_state: ProgressState,
        quality: int,
        now: Optional[datetime] = None,
        force_hard: bool = False  # Mark as Hard action
    ) -> AnswerResult:
        """
        Process user answer using Spec v8 5-state machine.
        
        Args:
            current_state: Current ProgressState
            quality: Score 0-7
            now: Current timestamp (UTC)
            force_hard: True if user manually marks as Hard
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # Unpack state
        c_state = getattr(current_state, 'custom_state', CustomState.NEW.value)
        interval = getattr(current_state, 'precise_interval', float(current_state.interval))
        correct_streak = current_state.correct_streak
        incorrect_streak = current_state.incorrect_streak
        hard_streak = getattr(current_state, 'hard_streak', 0)
        learning_reps = getattr(current_state, 'learning_reps', 0)
        reps = current_state.repetitions
        
        # Handle timezone for elapsed calculation
        last_reviewed = getattr(current_state, 'last_reviewed', None)
        if last_reviewed and last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=timezone.utc)
        
        # === MARK AS HARD (Manual Action) ===
        if force_hard:
            c_state = CustomState.HARD.value
            interval = 1.0  # 1 day
            hard_streak = 0
            correct_streak = 0
        
        # === STATE MACHINE ===
        
        # 1. STATE: NEW (Initialize) - Apply formula for first answer
        elif c_state == CustomState.NEW.value:
            c_state = CustomState.LEARNING.value
            
            # Apply formula based on quality (starting from floor 20 min)
            formula = LEARNING_FORMULAS.get(quality, LEARNING_FORMULAS[0])
            interval = formula(LEARNING_FLOOR_MINUTES)
            
            reps = 1
            learning_reps = 1
            if quality >= 3:
                correct_streak = 1
                incorrect_streak = 0
            else:
                incorrect_streak = 1
                correct_streak = 0
        
        # 2. STATE: LEARNING (Minutes)
        elif c_state == CustomState.LEARNING.value:
            current_min = max(LEARNING_FLOOR_MINUTES, interval)
            
            formula = LEARNING_FORMULAS.get(quality, LEARNING_FORMULAS[0])
            next_interval = formula(current_min)
            
            learning_reps += 1
            reps += 1
            
            # Safety Valve: 10 reps without graduation → HARD
            if learning_reps >= LEARNING_SAFETY_VALVE_REPS and next_interval <= LEARNING_GRADUATION_THRESHOLD:
                c_state = CustomState.HARD.value
                interval = 1.0  # 1 day
                correct_streak = 0
                hard_streak = 0
                learning_reps = 0
            elif next_interval > LEARNING_GRADUATION_THRESHOLD:
                # Graduate to REVIEW
                c_state = CustomState.REVIEW.value
                interval = next_interval / 1440.0  # Convert to days
                learning_reps = 0
            else:
                interval = next_interval
            
            # Update streaks
            if quality >= 3:
                correct_streak += 1
                incorrect_streak = 0
            else:
                incorrect_streak += 1
                correct_streak = 0
        
        # 3. STATE: REVIEW (Days)
        elif c_state == CustomState.REVIEW.value:
            current_days = max(1.0, interval)
            reps += 1
            
            if quality <= 1:
                # Fail → HARD
                c_state = CustomState.HARD.value
                interval = 1.0
                hard_streak = 0
                correct_streak = 0
                incorrect_streak += 1
            else:
                # Success
                multiplier = REVIEW_MULTIPLIERS.get(quality, 1.8)
                next_days = min(REVIEW_CEILING_DAYS, current_days * multiplier)
                interval = max(1.0, next_days)
                
                if quality >= 4:
                    correct_streak += 1
                    incorrect_streak = 0
                elif quality == 2:
                    # Score 2 (Khó) is penalty, reset streak
                    correct_streak = 0
                
                # Promotion to MASTER
                if correct_streak >= STREAK_TO_MASTER:
                    c_state = CustomState.MASTER.value
        
        # 4. STATE: HARD (Days)
        elif c_state == CustomState.HARD.value:
            current_days = max(1.0, interval)
            reps += 1
            
            formula = HARD_FORMULAS.get(quality, HARD_FORMULAS[0])
            next_days = formula(current_days)
            interval = max(1.0, next_days)
            
            if quality <= 2:
                # Score 0, 1, 2: Reset hard_streak
                hard_streak = 0
                incorrect_streak += 1
                correct_streak = 0
            elif quality >= 4:
                # Score 4-7: Increase hard_streak
                hard_streak += 1
                correct_streak += 1
                incorrect_streak = 0
            else:
                # Score 3: Keep hard_streak
                correct_streak += 1
                incorrect_streak = 0
            
            # Exit to REVIEW
            if hard_streak >= HARD_STREAK_TO_EXIT:
                c_state = CustomState.REVIEW.value
                hard_streak = 0
        
        # 5. STATE: MASTER (Days with 1.2x Bonus)
        elif c_state == CustomState.MASTER.value:
            current_days = max(1.0, interval)
            reps += 1
            
            if quality <= 2:
                # Soft Demotion: NOT to HARD, to REVIEW with 50%
                c_state = CustomState.REVIEW.value
                interval = max(3.0, current_days * 0.5)  # Min 3 days
                correct_streak = 0
                incorrect_streak += 1
            else:
                # Success with 1.2x bonus
                base_multiplier = REVIEW_MULTIPLIERS.get(quality, 1.8)
                bonus_multiplier = base_multiplier * 1.2
                next_days = min(REVIEW_CEILING_DAYS, current_days * bonus_multiplier)
                interval = max(1.0, next_days)
                
                if quality >= 4:
                    correct_streak += 1
                incorrect_streak = 0
        
        # === FINALIZE ===
        
        # Convert to integer minutes for storage
        if c_state == CustomState.LEARNING.value:
            interval_minutes = int(max(LEARNING_FLOOR_MINUTES, interval))
            precise = interval
        else:
            interval_minutes = int(max(1440, interval * 1440))  # Min 1 day
            precise = interval
        
        # Legacy status mapping
        status_map = {
            CustomState.NEW.value: 'new',
            CustomState.LEARNING.value: 'learning',
            CustomState.REVIEW.value: 'reviewing',
            CustomState.HARD.value: 'reviewing',
            CustomState.MASTER.value: 'mastered'
        }
        legacy_status = status_map.get(c_state, 'reviewing')
        
        new_mastery = MemoryEngine.calculate_mastery(c_state, reps, correct_streak)
        
        new_progress_state = ProgressState(
            status=legacy_status,
            mastery=new_mastery,
            repetitions=reps,
            interval=interval_minutes,
            correct_streak=correct_streak,
            incorrect_streak=incorrect_streak,
            easiness_factor=2.5,
            custom_state=c_state,
            hard_streak=hard_streak,
            learning_reps=learning_reps,
            precise_interval=precise
        )
        
        # Retention at t=0 (just answered)
        retention = 1.0
        memory_power = MemoryEngine.calculate_memory_power(new_mastery, retention)
        
        return AnswerResult(
            new_state=new_progress_state,
            memory_power=memory_power,
            retention_percent=100.0
        )

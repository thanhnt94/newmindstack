"""
Memory Power Engine - Core Calculations

This module implements the Memory Power system, replacing traditional SM-2 algorithm
with a simpler, intuitive formula:

    Memory Power (%) = Mastery × Retention

Where:
- Mastery: How well the knowledge is encoded (based on correct streaks)
- Retention: Probability of recall right now (decays over time)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, NamedTuple
from dataclasses import dataclass


# === CONSTANTS ===

# Learning phase: intervals in minutes for each successful repetition
LEARNING_INTERVALS_MINUTES = [1, 10, 60, 240, 480, 1440]  # 1m, 10m, 1h, 4h, 8h, 1d

# Graduating interval when moving from Learning -> Reviewing (in minutes)
GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60  # 4 days

# Relearning interval when failing in Review phase
RELEARNING_INTERVAL_MINUTES = 10

# Minimum interval (1 minute)
MIN_INTERVAL_MINUTES = 1

# Retention threshold for due items (90%)
RETENTION_THRESHOLD = 0.90

# Streak thresholds
LEARNING_TO_REVIEWING_STREAK = 7  # Graduate after 7 correct answers


@dataclass
class ProgressState:
    """Represents the state of a learning item."""
    status: str  # 'new', 'learning', 'reviewing'
    mastery: float  # 0.0 - 1.0
    repetitions: int
    interval: int  # minutes
    correct_streak: int
    incorrect_streak: int
    easiness_factor: float  # Still used for interval calculation


@dataclass
class AnswerResult:
    """Result of processing an answer."""
    new_state: ProgressState
    memory_power: float
    score_delta: int


class MemoryEngine:
    """
    Pure calculation engine for Memory Power system.
    No database access - all methods are static and use only provided inputs.
    """

    # === MASTERY CALCULATION ===
    
    @staticmethod
    def calculate_mastery(
        status: str,
        repetitions: int,
        correct_streak: int,
        incorrect_streak: int = 0
    ) -> float:
        """
        Calculate Mastery (0.0 - 1.0) based on learning status and streaks.

        Mastery ranges:
        - New: 0%
        - Learning (reps 1-7): 10% → 52% (linear growth)
        - Reviewing: 60% → 100% (slower growth, caps at 100%)

        Args:
            status: 'new', 'learning', or 'reviewing'
            repetitions: Total successful repetitions
            correct_streak: Current consecutive correct answers
            incorrect_streak: Current consecutive incorrect answers (reduces mastery)

        Returns:
            Mastery value between 0.0 and 1.0
        """
        if status == 'new':
            return 0.0
        
        elif status == 'learning':
            # Base: 10%, each rep adds 6%, max 52% (at 7 reps)
            # Streak bonus: extra 1% per streak after 3
            base = 0.10 + min(repetitions, 7) * 0.06
            streak_bonus = max(0, (correct_streak - 3)) * 0.01
            mastery = min(0.52, base + streak_bonus)
            
        elif status == 'reviewing':
            # Base: 60%, each rep adds ~5.7%, max 100%
            # Long correct streaks accelerate growth
            base = 0.60 + min(repetitions, 7) * 0.057
            streak_bonus = max(0, (correct_streak - 5)) * 0.02
            mastery = min(1.0, base + streak_bonus)
            
        else:
            mastery = 0.0

        # Apply incorrect streak penalty (safety buffer for high mastery)
        if incorrect_streak > 0:
            # Each incorrect reduces mastery, but high mastery has buffer
            penalty_per_error = 0.15 if mastery > 0.7 else 0.20
            penalty = min(incorrect_streak * penalty_per_error, mastery - 0.10)
            mastery = max(0.10, mastery - penalty)

        return round(mastery, 4)

    # === RETENTION CALCULATION (Forgetting Curve) ===

    @staticmethod
    def calculate_retention(
        last_reviewed: Optional[datetime],
        interval: int,
        now: Optional[datetime] = None
    ) -> float:
        """
        Calculate Retention (0.0 - 1.0) using the forgetting curve.

        Uses exponential decay: R = e^(-t/S)
        Where:
        - t = time elapsed since last review
        - S = stability (derived from interval)

        Args:
            last_reviewed: Timestamp of last review (timezone-aware)
            interval: Current interval in minutes
            now: Current time (defaults to now)

        Returns:
            Retention probability between 0.0 and 1.0
        """
        if last_reviewed is None:
            return 1.0  # Never reviewed = assume fresh if just learned

        if now is None:
            now = datetime.now(timezone.utc)

        # Ensure timezone awareness
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Time elapsed in minutes
        elapsed_minutes = (now - last_reviewed).total_seconds() / 60.0

        if elapsed_minutes <= 0:
            return 1.0

        # Stability = interval (the scheduled gap represents memory strength)
        # Using interval as a proxy for how "stable" the memory is
        stability = max(interval, 1)  # Avoid division by zero

        # Exponential decay: R = e^(-t/S)
        # We adjust the decay rate so that at t=interval, R ≈ 0.9 (90%)
        # ln(0.9) ≈ -0.105, so decay_rate ≈ 0.105 / interval
        decay_rate = 0.105 / stability
        retention = math.exp(-decay_rate * elapsed_minutes)

        return round(max(0.0, min(1.0, retention)), 4)

    # === MEMORY POWER ===

    @staticmethod
    def calculate_memory_power(mastery: float, retention: float) -> float:
        """
        Calculate Memory Power = Mastery × Retention.

        Args:
            mastery: Mastery value (0.0 - 1.0)
            retention: Retention value (0.0 - 1.0)

        Returns:
            Memory Power percentage (0.0 - 1.0)
        """
        return round(mastery * retention, 4)

    # === ANSWER PROCESSING ===

    @staticmethod
    def process_answer(
        current_state: ProgressState,
        quality: int,
        now: Optional[datetime] = None
    ) -> AnswerResult:
        """
        Process an answer and calculate new state.

        Quality Scale (0-5):
        - 5: Perfect, easy recall (Flashcard "Dễ", Typing 100%)
        - 4: Good recall with effort (Flashcard "Nhớ", Quiz correct)
        - 3: Correct but difficult (Flashcard "Khó")
        - 2: Incorrect but close / hint used
        - 1: Incorrect
        - 0: Complete blackout / forgot

        Args:
            current_state: Current ProgressState
            quality: Answer quality (0-5)
            now: Current timestamp

        Returns:
            AnswerResult with new state and memory power
        """
        if now is None:
            now = datetime.now(timezone.utc)

        status = current_state.status
        mastery = current_state.mastery
        reps = current_state.repetitions
        interval = current_state.interval
        ef = current_state.easiness_factor
        correct_streak = current_state.correct_streak
        incorrect_streak = current_state.incorrect_streak

        is_correct = quality >= 3
        score_delta = 0

        if is_correct:
            # === CORRECT ANSWER ===
            incorrect_streak = 0
            correct_streak += 1
            reps += 1

            # Score calculation
            if status == 'new':
                score_delta = 5  # First time bonus
            score_delta += 10 if quality >= 4 else 5

            # Status transitions
            if status == 'new':
                status = 'learning'
                interval = LEARNING_INTERVALS_MINUTES[0]

            elif status == 'learning':
                # Get next learning interval
                step_idx = min(reps - 1, len(LEARNING_INTERVALS_MINUTES) - 1)
                interval = LEARNING_INTERVALS_MINUTES[step_idx]

                # Check graduation to reviewing
                if reps >= LEARNING_TO_REVIEWING_STREAK and quality >= 4:
                    status = 'reviewing'
                    interval = GRADUATING_INTERVAL_MINUTES
                    reps = 1  # Reset for reviewing phase

            elif status == 'reviewing':
                # Update easiness factor (SM-2 style for interval calculation)
                ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
                ef = max(1.3, ef)

                # Calculate new interval
                interval = int(math.ceil(interval * ef))

                # Streak bonus: longer streaks = even longer intervals
                if correct_streak > 5:
                    streak_multiplier = 1.0 + (correct_streak - 5) * 0.05
                    interval = int(interval * min(streak_multiplier, 1.5))

        else:
            # === INCORRECT ANSWER ===
            correct_streak = 0
            incorrect_streak += 1

            # Compounding penalty based on consecutive errors
            if status == 'reviewing':
                if incorrect_streak >= 3:
                    # Hard reset: back to learning
                    status = 'learning'
                    reps = 0
                    mastery = 0.10
                elif incorrect_streak == 2:
                    # Heavy penalty
                    mastery = max(0.20, mastery * 0.5)
                    reps = max(0, reps - 3)
                else:
                    # Light penalty (first mistake has buffer)
                    mastery = max(0.40, mastery * 0.8)
                    reps = max(0, reps - 1)

                interval = RELEARNING_INTERVAL_MINUTES
                ef = max(1.3, ef - 0.2)

            elif status == 'learning':
                if incorrect_streak >= 2:
                    reps = 0  # Reset learning progress
                    mastery = 0.10
                interval = RELEARNING_INTERVAL_MINUTES

            elif status == 'new':
                status = 'learning'
                interval = RELEARNING_INTERVAL_MINUTES

        # Recalculate mastery based on new state
        new_mastery = MemoryEngine.calculate_mastery(
            status, reps, correct_streak, incorrect_streak
        )

        # Ensure interval minimum
        interval = max(MIN_INTERVAL_MINUTES, interval)

        new_state = ProgressState(
            status=status,
            mastery=new_mastery,
            repetitions=reps,
            interval=interval,
            correct_streak=correct_streak,
            incorrect_streak=incorrect_streak,
            easiness_factor=round(ef, 4)
        )

        # Calculate current memory power (assuming 100% retention right after answer)
        memory_power = MemoryEngine.calculate_memory_power(new_mastery, 1.0)

        return AnswerResult(
            new_state=new_state,
            memory_power=memory_power,
            score_delta=score_delta
        )

    # === UTILITY: Quality Mapping by Mode ===

    @staticmethod
    def flashcard_rating_to_quality(rating: int, button_count: int = 3) -> int:
        """
        Map flashcard button rating to quality score.

        3-button mode:
        - Button 1 (Forgot): quality 1
        - Button 2 (Hard): quality 3
        - Button 3 (Easy): quality 5

        4-button mode:
        - Button 1 (Forgot): quality 0
        - Button 2 (Hard): quality 2
        - Button 3 (Good): quality 4
        - Button 4 (Easy): quality 5
        """
        if button_count == 3:
            mapping = {1: 1, 2: 3, 3: 5}
        elif button_count == 4:
            mapping = {1: 0, 2: 2, 3: 4, 4: 5}
        else:
            # Default: treat as 0-5 directly
            return max(0, min(5, rating))

        return mapping.get(rating, 3)

    @staticmethod
    def quiz_answer_to_quality(is_correct: bool) -> int:
        """Map quiz answer to quality score."""
        return 4 if is_correct else 1

    @staticmethod
    def typing_accuracy_to_quality(accuracy: float, used_hint: bool = False) -> int:
        """
        Map typing accuracy to quality score.

        Args:
            accuracy: 0.0 - 1.0 (percentage of correct characters)
            used_hint: Whether user requested a hint
        """
        if used_hint:
            return 2  # Hint used = borderline pass

        if accuracy >= 1.0:
            return 5  # Perfect
        elif accuracy >= 0.9:
            return 4  # Minor typo
        elif accuracy >= 0.7:
            return 3  # Mostly correct
        elif accuracy >= 0.5:
            return 2  # Half correct
        else:
            return 1  # Wrong

    # === DUE TIME CALCULATION ===

    @staticmethod
    def calculate_due_time(
        last_reviewed: datetime,
        interval: int
    ) -> datetime:
        """Calculate when item is due for review."""
        return last_reviewed + timedelta(minutes=interval)

    @staticmethod
    def is_due(
        due_time: Optional[datetime],
        now: Optional[datetime] = None
    ) -> bool:
        """Check if item is due for review."""
        if due_time is None:
            return True  # Never reviewed = due

        if now is None:
            now = datetime.now(timezone.utc)

        if due_time.tzinfo is None:
            due_time = due_time.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        return now >= due_time

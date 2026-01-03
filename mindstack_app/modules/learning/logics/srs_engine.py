"""
SRS Engine - Pure Spaced Repetition System Logic

Pure functions for SRS calculations following SM-2 algorithm.
No database access - only calculations based on inputs.

This engine provides:
- SM-2 state transitions
- Interval calculations
- Quality normalization (Cognitive Load Heuristic)
- Retention/forgetting curve calculations
"""

import datetime
import math
from typing import Tuple
from enum import Enum


class SrsConstants:
    """Constants for SRS algorithm"""
    LEARNING_STEPS_MINUTES = [10, 60, 240, 480, 1440, 2880]  # Learning phase intervals
    RELEARNING_STEP_MINUTES = 10  # Reset interval on failure
    GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60  # 4 days graduation
    MIN_EASINESS_FACTOR = 1.3  # Minimum EF value
    DEFAULT_EASINESS_FACTOR = 2.5  # Starting EF


class LearningMode(Enum):
    """Learning modes with different cognitive loads"""
    FLASHCARD = "flashcard"
    MCQ = "mcq"
    QUIZ = "quiz"
    MATCHING = "matching"
    LISTENING = "listening"
    TYPING = "typing"
    SPEED = "speed"
    MEMRISE = "memrise"


class SrsEngine:
    """
    Pure calculation engine for Spaced Repetition System.
    All methods are static and use only provided inputs (no DB access).
    """

    # ===  SM-2 Algorithm ===

    @staticmethod
    def calculate_next_state(
        current_status: str,
        current_interval: int,
        current_ef: float,
        current_reps: int,
        quality: int
    ) -> Tuple[str, int, float, int]:
        """
        Pure function to calculate next SRS state using SM-2 algorithm.
        
        Args:
            current_status: Current learning status ('new', 'learning', 'reviewing')
            current_interval: Current interval in minutes
            current_ef: Current easiness factor
            current_reps: Current repetition count
            quality: Answer quality (0-5)
        
        Returns:
            Tuple of (new_status, new_interval_minutes, new_ef, new_reps)
        """
        new_status = current_status
        new_interval = current_interval
        new_ef = current_ef
        new_reps = current_reps

        if current_status in ['learning', 'new']:
            if quality < 3:
                # Failed - reset to relearning
                new_status = 'learning'
                new_interval = SrsConstants.RELEARNING_STEP_MINUTES
                new_reps = 0
            else:
                # Correct - progress through learning steps
                new_status = 'learning'
                new_reps = current_reps + 1
                new_interval = SrsEngine.get_learning_interval(new_reps)
        
        elif current_status == 'reviewing':
            if quality < 3:
                # Failed review - back to learning
                new_status = 'learning'
                new_reps = 0
                new_ef = max(SrsConstants.MIN_EASINESS_FACTOR, current_ef - 0.2)
                new_interval = SrsConstants.RELEARNING_STEP_MINUTES
            else:
                # Successful review - recalculate EF and interval
                new_reps = current_reps + 1
                
                # SM-2 EF formula: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q)*0.02))
                q = quality
                new_ef = current_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
                new_ef = max(SrsConstants.MIN_EASINESS_FACTOR, new_ef)
                
                # Interval increases by EF multiplier
                new_interval = math.ceil(current_interval * new_ef)

        return new_status, new_interval, new_ef, new_reps

    @staticmethod
    def get_learning_interval(repetitions: int) -> int:
        """
        Get interval for learning phase based on repetition count.
        
        Args:
            repetitions: Number of successful repetitions
        
        Returns:
            Interval in minutes for next review
        """
        step_index = repetitions - 1
        if 0 <= step_index < len(SrsConstants.LEARNING_STEPS_MINUTES):
            return SrsConstants.LEARNING_STEPS_MINUTES[step_index]
        return SrsConstants.LEARNING_STEPS_MINUTES[-1]

    @staticmethod
    def should_graduate(repetitions: int, quality: int) -> bool:
        """
        Check if item should graduate from learning to reviewing.
        
        Args:
            repetitions: Number of successful repetitions
            quality: Last answer quality
        
        Returns:
            True if should graduate to reviewing phase
        """
        return repetitions >= 7 and quality >= 4

    # === Quality Normalization (Cognitive Load Heuristic) ===

    @staticmethod
    def normalize_quality(mode: str, result_data: dict) -> int:
        """
        Implements the "Cognitive Load Heuristic" to map mode-specific results 
        to standard SRS Quality (0-5).

        Strategy:
        - Flashcard: User Self-Report (1-5)
        - MCQ/Matching (Recognition - Low Load): Correct → 4, Wrong → 1
        - Listening/Typing (Production - High Load): Based on accuracy
        
        Args:
            mode: Learning mode ('flashcard', 'mcq', 'listening', etc.)
            result_data: Mode-specific result data (quality, is_correct, accuracy, etc.)
        
        Returns:
            Normalized SRS quality (0-5)
        """
        mode = mode.lower()

        # --- FLASHCARD (Direct Self-Report) ---
        if mode == 'flashcard':
            if 'quality' in result_data:
                return int(result_data['quality'])
            
            # Map string ratings if present
            rating_map = {
                'fail': 0, 'again': 1, 
                'hard': 3, 'vague': 2,
                'good': 4, 'easy': 5, 'very_easy': 5
            }
            rating = str(result_data.get('rating', 'good')).lower()
            return rating_map.get(rating, 4)

        # --- MCQ / MATCHING (Recognition - Low Cognitive Load) ---
        elif mode in ['mcq', 'quiz', 'matching']:
            is_correct = result_data.get('is_correct', False) or result_data.get('correct', False)
            return 4 if is_correct else 1

        # --- LISTENING / TYPING (Production - High Cognitive Load) ---
        elif mode in ['listening', 'typing']:
            accuracy = float(result_data.get('accuracy', 0))
            if accuracy >= 1.0:
                return 5  # Perfect
            elif accuracy >= 0.85:
                return 4  # Good
            else:
                return 1  # Fail

        # Fallback default
        return 4

    # === Retention & Forgetting Curve ===

    @staticmethod
    def calculate_retention(
        last_reviewed: datetime.datetime,
        interval_minutes: int,
        now: datetime.datetime = None
    ) -> float:
        """
        Calculate retention probability using Forgetting Curve: R = e^(-t/S)
        
        Where:
        - t is time elapsed since last review
        - S is memory stability (derived from interval)
        - Assumes 90% retention at the scheduled due time
        
        Args:
            last_reviewed: When item was last reviewed
            interval_minutes: Scheduled interval in minutes
            now: Current time (default: datetime.now(UTC))
        
        Returns:
            Retention rate as decimal (0.0-1.0)
        """
        if not last_reviewed or interval_minutes <= 0:
            return 0.0
        
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        
        # Ensure timezone aware
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=datetime.timezone.utc)
        
        elapsed_minutes = (now - last_reviewed).total_seconds() / 60
        if elapsed_minutes < 0:
            elapsed_minutes = 0
        
        # Memory stability: S = -interval / ln(0.9)
        # This assumes 90% retention at exactly the scheduled due time
        stability = -interval_minutes / math.log(0.9)
        
        # Retention: R = e^(-elapsed / stability)
        retention = math.exp(-elapsed_minutes / stability)
        
        return min(1.0, max(0.0, retention))

    @staticmethod
    def calculate_retention_percentage(
        last_reviewed: datetime.datetime,
        interval_minutes: int
    ) -> int:
        """
        Calculate retention as percentage (0-100).
        Convenience wrapper around calculate_retention().
        
        Args:
            last_reviewed: When item was last reviewed
            interval_minutes: Scheduled interval in minutes
        
        Returns:
            Retention percentage (0-100)
        """
        retention = SrsEngine.calculate_retention(last_reviewed, interval_minutes)
        return int(retention * 100)

    # === Utility Methods ===

    @staticmethod
    def quality_to_description(quality: int) -> str:
        """Convert quality value to human-readable description."""
        descriptions = {
            0: "Complete Fail",
            1: "Again / Failed",
            2: "Hard (vague)",
            3: "Hard",
            4: "Good",
            5: "Perfect / Easy"
        }
        return descriptions.get(quality, "Unknown")

    @staticmethod
    def is_correct(quality: int) -> bool:
        """Determine if quality represents a correct answer."""
        return quality >= 3

"""
Scoring Engine - Gamification Points Calculation

Pure logic for calculating points from learning activities.
No database access - only calculations based on inputs.

Points are awarded for:
- First-time learning
- Correct answers (scaled by difficulty/mode)
- Streak bonuses
- Daily goals achievement
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class LearningMode(Enum):
    """Learning modes with different point multipliers."""
    FLASHCARD = "flashcard"
    QUIZ_MCQ = "quiz_mcq"
    TYPING = "typing"
    LISTENING = "listening"
    MATCHING = "matching"
    SPEED = "speed"
    MEMRISE = "memrise"


@dataclass
class ScoreResult:
    """Result of a scoring calculation."""
    base_points: int
    bonus_points: int
    total_points: int
    breakdown: dict[str, int]
    reason: str


class ScoringEngine:
    """
    Pure calculation engine for gamification scoring.
    No database access - all methods are static and use only provided inputs.
    """

    # === BASE POINTS BY MODE ===
    
    # Base points for correct answers by learning mode
    MODE_BASE_POINTS = {
        LearningMode.FLASHCARD: 10,
        LearningMode.QUIZ_MCQ: 10,
        LearningMode.TYPING: 15,      # Harder = more points
        LearningMode.LISTENING: 12,
        LearningMode.MATCHING: 8,
        LearningMode.SPEED: 20,       # Time pressure = more points
        LearningMode.MEMRISE: 12,
    }
    
    # First-time bonus (learning a new item)
    FIRST_TIME_BONUS = 5
    
    # Streak bonus thresholds
    STREAK_BONUS_THRESHOLDS = [
        (3, 2),    # 3+ streak: +2 points
        (5, 5),    # 5+ streak: +5 points
        (10, 10),  # 10+ streak: +10 points
        (20, 20),  # 20+ streak: +20 points
        (50, 50),  # 50+ streak: +50 points
    ]
    
    # Perfect answer bonus (quality = 5)
    PERFECT_BONUS = 5
    
    # Speed bonus multipliers (based on response time)
    SPEED_MULTIPLIERS = [
        (1.0, 1.5),   # Under 1 second: 1.5x
        (2.0, 1.3),   # Under 2 seconds: 1.3x
        (3.0, 1.1),   # Under 3 seconds: 1.1x
    ]

    # === MAIN SCORING METHODS ===

    @staticmethod
    def calculate_answer_points(
        mode: LearningMode | str,
        quality: int,
        is_correct: bool,
        is_first_time: bool = False,
        correct_streak: int = 0,
        response_time_seconds: Optional[float] = None,
        base_points_override: Optional[int] = None
    ) -> ScoreResult:
        """
        Calculate points for answering a learning item using Fixed FSRS Scoring.
        
        Args:
            mode: Learning mode
            quality: FSRS Rating (1=Again, 2=Hard, 3=Good, 4=Easy)
            is_correct: Whether the answer was correct (rating >= 2)
            is_first_time: Whether this is the first time seeing this item
            correct_streak: Current consecutive correct answers
            response_time_seconds: (Ignored in fixed model)
            base_points_override: (Ignored in fixed model)

        Returns:
            ScoreResult with breakdown of points earned
        """
        # 1. Map Reality to Config Keys
        from flask import current_app
        
        score_map = {
            1: current_app.config.get('SCORE_FSRS_AGAIN', 1),
            2: current_app.config.get('SCORE_FSRS_HARD', 5),
            3: current_app.config.get('SCORE_FSRS_GOOD', 10),
            4: current_app.config.get('SCORE_FSRS_EASY', 15)
        }
        
        base = score_map.get(quality, 0)
        
        breakdown: dict[str, int] = {}
        breakdown['base'] = base
        total = base
        
        reasons: list[str] = [f"Rating {quality}"]
        
        # 2. Simplified Streak Bonus (Every 10 streaks)
        bonus = 0
        if is_correct and correct_streak > 0 and correct_streak % 10 == 0:
            bonus = 5
            breakdown['streak_bonus'] = bonus
            total += bonus
            reasons.append(f"Streak {correct_streak}")
            
        reason = " + ".join(reasons)

        return ScoreResult(
            base_points=base,
            bonus_points=bonus,
            total_points=total,
            breakdown=breakdown,
            reason=reason
        )

    @staticmethod
    def calculate_session_bonus(
        items_reviewed: int,
        items_correct: int,
        session_duration_minutes: float,
        daily_goal_met: bool = False
    ) -> ScoreResult:
        """
        Calculate bonus points for completing a study session.

        Args:
            items_reviewed: Total items reviewed in session
            items_correct: Number of correct answers
            session_duration_minutes: Total session time
            daily_goal_met: Whether daily goal was achieved

        Returns:
            ScoreResult with session completion bonuses
        """
        breakdown: dict[str, int] = {}
        total = 0
        reasons: list[str] = []

        # Minimum session to qualify (at least 5 items)
        if items_reviewed < 5:
            return ScoreResult(
                base_points=0,
                bonus_points=0,
                total_points=0,
                breakdown={},
                reason="Session too short"
            )

        # === COMPLETION BONUS ===
        # 1 point per item reviewed
        completion = items_reviewed
        breakdown['completion'] = completion
        total += completion
        reasons.append(f"Reviewed {items_reviewed}")

        # === ACCURACY BONUS ===
        accuracy = items_correct / items_reviewed if items_reviewed > 0 else 0
        if accuracy >= 0.9:
            accuracy_bonus = 20
        elif accuracy >= 0.8:
            accuracy_bonus = 10
        elif accuracy >= 0.7:
            accuracy_bonus = 5
        else:
            accuracy_bonus = 0
        
        if accuracy_bonus > 0:
            breakdown['accuracy'] = accuracy_bonus
            total += accuracy_bonus
            reasons.append(f"{accuracy*100:.0f}% accuracy")

        # === FOCUS BONUS ===
        # Bonus for sustained study (10+ minutes)
        if session_duration_minutes >= 30:
            focus_bonus = 30
        elif session_duration_minutes >= 20:
            focus_bonus = 20
        elif session_duration_minutes >= 10:
            focus_bonus = 10
        else:
            focus_bonus = 0
        
        if focus_bonus > 0:
            breakdown['focus'] = focus_bonus
            total += focus_bonus
            reasons.append(f"{session_duration_minutes:.0f}min focus")

        # === DAILY GOAL BONUS ===
        if daily_goal_met:
            goal_bonus = 50
            breakdown['daily_goal'] = goal_bonus
            total += goal_bonus
            reasons.append("Daily goal met!")

        reason = " + ".join(reasons)

        return ScoreResult(
            base_points=completion,
            bonus_points=total - completion,
            total_points=total,
            breakdown=breakdown,
            reason=reason
        )

    @staticmethod
    def calculate_daily_streak_bonus(daily_streak: int) -> ScoreResult:
        """
        Calculate bonus for maintaining a daily study streak.

        Args:
            daily_streak: Number of consecutive days studied

        Returns:
            ScoreResult with daily streak bonus
        """
        if daily_streak < 2:
            return ScoreResult(
                base_points=0,
                bonus_points=0,
                total_points=0,
                breakdown={},
                reason="No streak"
            )

        # Progressive bonus for longer streaks
        if daily_streak >= 365:
            bonus = 500
        elif daily_streak >= 100:
            bonus = 200
        elif daily_streak >= 30:
            bonus = 100
        elif daily_streak >= 14:
            bonus = 50
        elif daily_streak >= 7:
            bonus = 25
        elif daily_streak >= 3:
            bonus = 10
        else:
            bonus = 5

        return ScoreResult(
            base_points=0,
            bonus_points=bonus,
            total_points=bonus,
            breakdown={'daily_streak': bonus},
            reason=f"{daily_streak}-day streak!"
        )

    # === UTILITY METHODS ===

    @staticmethod
    def quality_to_score(quality: int) -> int:
        """
        Pure function: Convert SRS quality (0-5) to score points.
        
        This is the single source of truth for quality-to-score mapping.
        Used by SRS service when saving ReviewLog.score_change.
        
        Args:
            quality: SRS quality rating (0-5)
                0 = Complete fail
                1 = Again/Failed
                2 = Hard (vague)
                3 = Hard
                4 = Good
                5 = Perfect/Easy
        
        Returns:
            Score points (0-20)
        """
        score_map = {
            0: 0,    # Complete fail
            1: 5,    # Failed/Again
            2: 8,    # Hard (vague)
            3: 10,   # Hard
            4: 15,   # Good
            5: 20    # Perfect/Easy
        }
        return score_map.get(quality, 10)  # Default to 10 if unknown

    @staticmethod
    def quiz_answer_to_quality(is_correct: bool) -> int:
        """Convert quiz correct/incorrect to quality score."""
        return 4 if is_correct else 1

    @staticmethod
    def get_mode_from_string(mode_string: str) -> LearningMode:
        """Convert string to LearningMode enum."""
        try:
            return LearningMode(mode_string.lower())
        except ValueError:
            return LearningMode.FLASHCARD

    @staticmethod
    def get_point_value_for_mode(mode: LearningMode | str) -> int:
        """Get base point value for a learning mode."""
        if isinstance(mode, str):
            mode = ScoringEngine.get_mode_from_string(mode)
        return ScoringEngine.MODE_BASE_POINTS.get(mode, 10)

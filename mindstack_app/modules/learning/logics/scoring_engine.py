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
        from mindstack_app.models import AppSettings
        
        # 1. Map Reality to Config Keys
        score_map = {
            1: AppSettings.get('SCORE_FSRS_AGAIN'),
            2: AppSettings.get('SCORE_FSRS_HARD'),
            3: AppSettings.get('SCORE_FSRS_GOOD'),
            4: AppSettings.get('SCORE_FSRS_EASY')
        }
        
        base = score_map.get(quality, 0)
        
        breakdown: dict[str, int] = {}
        breakdown['base'] = base
        total = base
        
        reasons: list[str] = [f"Rating {quality}"]
        
        # 2. Simplified Streak Bonus
        bonus = 0
        bonus_modulo = AppSettings.get('SCORING_STREAK_BONUS_MODULO')
        if is_correct and correct_streak > 0 and correct_streak % bonus_modulo == 0:
            bonus = AppSettings.get('SCORING_STREAK_BONUS_VALUE')
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
        """
        from mindstack_app.models import AppSettings
        breakdown: dict[str, int] = {}
        total = 0
        reasons: list[str] = []

        if items_reviewed < 5:
            return ScoreResult(0, 0, 0, {}, "Session too short")

        # 1 point per item reviewed (hardcoded for now as it's a direct metric)
        completion = items_reviewed
        breakdown['completion'] = completion
        total += completion
        reasons.append(f"Reviewed {items_reviewed}")

        # === ACCURACY BONUS ===
        accuracy = items_correct / items_reviewed if items_reviewed > 0 else 0
        accuracy_bonus = 0
        if accuracy >= 0.9:
            accuracy_bonus = 20
        elif accuracy >= 0.8:
            accuracy_bonus = 10
        elif accuracy >= 0.7:
            accuracy_bonus = 5
        
        if accuracy_bonus > 0:
            breakdown['accuracy'] = accuracy_bonus
            total += accuracy_bonus
            reasons.append(f"{accuracy*100:.0f}% accuracy")

        # === FOCUS BONUS ===
        focus_bonus = 0
        if session_duration_minutes >= 30:
            focus_bonus = 30
        elif session_duration_minutes >= 20:
            focus_bonus = 20
        elif session_duration_minutes >= 10:
            focus_bonus = 10
        
        if focus_bonus > 0:
            breakdown['focus'] = focus_bonus
            total += focus_bonus
            reasons.append(f"{session_duration_minutes:.0f}min focus")

        # === DAILY GOAL BONUS ===
        if daily_goal_met:
            goal_bonus = AppSettings.get('DAILY_GOAL_SCORE', 50)
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
        """
        from mindstack_app.models import AppSettings
        if daily_streak < 2:
            return ScoreResult(0, 0, 0, {}, "No streak")

        # Progressive bonus for longer streaks
        if daily_streak >= 365:
            bonus = AppSettings.get('SCORING_STREAK_LVL_1Y')
        elif daily_streak >= 100:
            bonus = AppSettings.get('SCORING_STREAK_LVL_100D')
        elif daily_streak >= 30:
            bonus = AppSettings.get('SCORING_STREAK_LVL_30D')
        elif daily_streak >= 14:
            bonus = AppSettings.get('SCORING_STREAK_LVL_14D')
        elif daily_streak >= 7:
            bonus = AppSettings.get('SCORING_STREAK_LVL_7D')
        elif daily_streak >= 3:
            bonus = AppSettings.get('SCORING_STREAK_LVL_3D')
        else:
            bonus = AppSettings.get('SCORING_STREAK_LVL_2D')

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
            1: 5,    # Again (Failed) - 5 pts
            2: 10,   # Hard - 10 pts
            3: 15,   # Good - 15 pts
            4: 20    # Easy - 20 pts
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

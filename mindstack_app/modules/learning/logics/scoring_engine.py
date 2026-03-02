"""
Scoring Engine - Gamification Points Calculation
=================================================
Thin adapter layer. All per-answer scoring is delegated to the centralized
`scoring.logics.calculator.ScoreCalculator`.  Session-level bonuses and daily
streak bonuses are handled locally using AppSettings.

This module is kept for backward compatibility with callers that go through
`LearningInterface.calculate_answer_points`.
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
        base_points_override: Optional[int] = None,
        stability: float = 0.0,
        difficulty: float = 5.0
    ) -> ScoreResult:
        """
        Calculate points for answering a learning item.
        Delegates to the centralized ScoreCalculator for consistency.
        """
        from mindstack_app.modules.scoring.logics.calculator import ScoreCalculator
        
        # Map quality to config event key
        config_keys = {
            1: 'SCORE_FSRS_AGAIN',
            2: 'SCORE_FSRS_HARD',
            3: 'SCORE_FSRS_GOOD',
            4: 'SCORE_FSRS_EASY'
        }
        event_key = config_keys.get(quality, 'SCORE_FSRS_GOOD')
        
        context = {
            'difficulty': difficulty,
            'stability': stability,
            'streak': correct_streak,
            'is_correct': is_correct,
            'duration_ms': int(response_time_seconds * 1000) if response_time_seconds else 0
        }
        
        total_score, breakdown = ScoreCalculator.calculate(event_key, context)
        
        base = breakdown.get('base', 0)
        
        return ScoreResult(
            base_points=base,
            bonus_points=total_score - base,
            total_points=total_score,
            breakdown=breakdown,
            reason=f"Rating {quality}"
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
    def quiz_answer_to_quality(is_correct: bool) -> int:
        """Convert quiz correct/incorrect to quality score."""
        return 4 if is_correct else 1

    @staticmethod
    def quality_to_score(quality: int) -> int:
        """Convert FSRS quality (1-4) to score points using centralized config."""
        from mindstack_app.modules.scoring.services.scoring_config_service import ScoringConfigService
        config_keys = {1: 'SCORE_FSRS_AGAIN', 2: 'SCORE_FSRS_HARD', 3: 'SCORE_FSRS_GOOD', 4: 'SCORE_FSRS_EASY'}
        key = config_keys.get(quality, 'SCORE_FSRS_GOOD')
        return int(ScoringConfigService.get_config(key) or 0)


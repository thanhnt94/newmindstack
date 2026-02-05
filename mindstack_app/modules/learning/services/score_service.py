"""
Learning Score Service
[DEPRECATED]
This service is deprecated. Please use `gamification` module services directly
for awarding points/XP. `learning` module is now focused on Academic Progress.

Service layer that connects ScoringEngine (pure logic) with 
Gamification module (database operations).

This is the integration point between:
- learning.core.logics.ScoringEngine (pure calculations)
- gamification.services.ScoreService (DB operations, badges)
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone

from mindstack_app.models import db
from mindstack_app.modules.gamification.services.scoring_service import ScoreService

from ..logics.scoring_engine import ScoringEngine, ScoreResult, LearningMode


def typing_accuracy_to_quality(accuracy: float, used_hint: bool = False) -> int:
    """Convert typing accuracy to FSRS quality rating 1-4."""
    if used_hint:
        return 2 if accuracy >= 0.7 else 1  # Hard or Again
    if accuracy >= 0.95:
        return 4  # Easy
    elif accuracy >= 0.7:
        return 3  # Good
    elif accuracy >= 0.4:
        return 2  # Hard
    else:
        return 1  # Again


class LearningScoreService:
    """
    Integration service connecting learning activities to gamification.
    
    This service:
    1. Uses ScoringEngine to calculate points from pure logic
    2. Calls ScoreService.award_points() to persist to database
    3. Triggers badge checks automatically
    """

    @staticmethod
    def record_flashcard_answer(
        user_id: int,
        item_id: int,
        quality: int,
        is_correct: bool,
        correct_streak: int = 0,
        is_first_time: bool = False
    ) -> dict:
        """
        Record a flashcard answer and award points.
        
        Args:
            user_id: User ID
            item_id: Flashcard item ID
            quality: Answer quality (1-4 FSRS rating)
            is_correct: Whether answer was correct
            correct_streak: Current correct answer streak
            is_first_time: Whether this is first time seeing item
            
        Returns:
            Dict with points awarded and breakdown
        """
        # Calculate points using pure logic
        score_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=correct_streak
        )
        
        # Skip if no points to award
        if score_result.total_points == 0:
            return {
                'success': True,
                'points_awarded': 0,
                'reason': score_result.reason,
                'breakdown': score_result.breakdown
            }
        
        # Persist to database via gamification service
        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_result.total_points,
            reason=score_result.reason,
            item_id=item_id,
            item_type='FLASHCARD'
        )
        
        return {
            'success': result.get('success', False),
            'points_awarded': score_result.total_points,
            'new_total': result.get('new_total'),
            'reason': score_result.reason,
            'breakdown': score_result.breakdown
        }

    @staticmethod
    def record_quiz_answer(
        user_id: int,
        item_id: int,
        is_correct: bool,
        correct_streak: int = 0,
        is_first_time: bool = False
    ) -> dict:
        """
        Record a quiz answer and award points.
        
        Args:
            user_id: User ID
            item_id: Quiz item ID
            is_correct: Whether answer was correct
            correct_streak: Current correct answer streak
            is_first_time: Whether this is first time seeing item
            
        Returns:
            Dict with points awarded and breakdown
        """
        quality = ScoringEngine.quiz_answer_to_quality(is_correct)
        
        score_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.QUIZ_MCQ,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=correct_streak
        )
        
        if score_result.total_points == 0:
            return {
                'success': True,
                'points_awarded': 0,
                'reason': score_result.reason,
                'breakdown': score_result.breakdown
            }
        
        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_result.total_points,
            reason=score_result.reason,
            item_id=item_id,
            item_type='QUIZ'
        )
        
        return {
            'success': result.get('success', False),
            'points_awarded': score_result.total_points,
            'new_total': result.get('new_total'),
            'reason': score_result.reason,
            'breakdown': score_result.breakdown
        }

    @staticmethod
    def record_typing_answer(
        user_id: int,
        item_id: int,
        accuracy: float,
        used_hint: bool = False,
        correct_streak: int = 0,
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None
    ) -> dict:
        """
        Record a typing exercise answer and award points.
        
        Args:
            user_id: User ID
            item_id: Item ID
            accuracy: Typing accuracy 0.0-1.0
            used_hint: Whether hint was used
            correct_streak: Current correct streak
            is_first_time: First time seeing item
            response_time_seconds: Time taken (for speed bonus)
            
        Returns:
            Dict with points awarded and breakdown
        """
        quality = typing_accuracy_to_quality(accuracy, used_hint)
        is_correct = accuracy >= 0.7  # 70% threshold for "correct"
        
        score_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.TYPING,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=correct_streak,
            response_time_seconds=response_time_seconds
        )
        
        if score_result.total_points == 0:
            return {
                'success': True,
                'points_awarded': 0,
                'reason': score_result.reason,
                'breakdown': score_result.breakdown
            }
        
        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_result.total_points,
            reason=score_result.reason,
            item_id=item_id,
            item_type='TYPING'
        )
        
        return {
            'success': result.get('success', False),
            'points_awarded': score_result.total_points,
            'new_total': result.get('new_total'),
            'reason': score_result.reason,
            'breakdown': score_result.breakdown
        }

    @staticmethod
    def record_session_complete(
        user_id: int,
        items_reviewed: int,
        items_correct: int,
        session_duration_minutes: float,
        daily_goal_met: bool = False
    ) -> dict:
        """
        Record session completion and award bonus points.
        
        Args:
            user_id: User ID
            items_reviewed: Total items reviewed
            items_correct: Number correct
            session_duration_minutes: Session duration
            daily_goal_met: Whether daily goal was achieved
            
        Returns:
            Dict with bonus points awarded
        """
        score_result = ScoringEngine.calculate_session_bonus(
            items_reviewed=items_reviewed,
            items_correct=items_correct,
            session_duration_minutes=session_duration_minutes,
            daily_goal_met=daily_goal_met
        )
        
        if score_result.total_points == 0:
            return {
                'success': True,
                'bonus_points': 0,
                'reason': score_result.reason,
                'breakdown': score_result.breakdown
            }
        
        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_result.total_points,
            reason=score_result.reason,
            item_type='SESSION_BONUS'
        )
        
        return {
            'success': result.get('success', False),
            'bonus_points': score_result.total_points,
            'new_total': result.get('new_total'),
            'reason': score_result.reason,
            'breakdown': score_result.breakdown
        }

    @staticmethod
    def award_daily_streak_bonus(user_id: int, daily_streak: int) -> dict:
        """
        Award bonus for maintaining daily study streak.
        
        Args:
            user_id: User ID
            daily_streak: Number of consecutive days
            
        Returns:
            Dict with streak bonus awarded
        """
        score_result = ScoringEngine.calculate_daily_streak_bonus(daily_streak)
        
        if score_result.total_points == 0:
            return {
                'success': True,
                'bonus_points': 0,
                'reason': score_result.reason
            }
        
        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_result.total_points,
            reason=score_result.reason,
            item_type='STREAK_BONUS'
        )
        
        return {
            'success': result.get('success', False),
            'bonus_points': score_result.total_points,
            'new_total': result.get('new_total'),
            'reason': score_result.reason
        }


# Convenience function for quick integration
def award_learning_points(
    user_id: int,
    item_id: int,
    mode: str,
    is_correct: bool,
    quality: int = 4,
    **kwargs
) -> dict:
    """
    Quick function to award points for any learning activity.
    
    Args:
        user_id: User ID
        item_id: Learning item ID
        mode: 'flashcard', 'quiz', 'typing', etc.
        is_correct: Whether answer was correct
        quality: Answer quality 0-5 (default 4)
        **kwargs: Additional params (correct_streak, is_first_time, etc.)
        
    Returns:
        Dict with points info
    """
    score_result = ScoringEngine.calculate_answer_points(
        mode=mode,
        quality=quality,
        is_correct=is_correct,
        is_first_time=kwargs.get('is_first_time', False),
        correct_streak=kwargs.get('correct_streak', 0),
        response_time_seconds=kwargs.get('response_time_seconds'),
        stability=kwargs.get('stability', 0.0),
        difficulty=kwargs.get('difficulty', 5.0)
    )
    
    if score_result.total_points == 0:
        return {'success': True, 'points_awarded': 0}
    
    result = ScoreService.award_points(
        user_id=user_id,
        amount=score_result.total_points,
        reason=score_result.reason,
        item_id=item_id,
        item_type=mode.upper()
    )
    
    return {
        'success': result.get('success', False),
        'points_awarded': score_result.total_points,
        'new_total': result.get('new_total'),
        'breakdown': score_result.breakdown
    }

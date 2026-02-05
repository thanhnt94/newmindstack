"""
Learning Module Interface
=========================

Public API for accessing Learning capabilities:
- Evaluation (Grading) of submissions
- Progress Tracking (Course completion stats)
- Metrics & Analytics (Delegated)

This interface decouples consumers (Quiz, Typing, Stats, etc.) from the internal logic.
"""

from typing import Any, Dict, Optional, List
from mindstack_app.modules.learning.logics.marker import compare_text, evaluate_multiple_choice
from mindstack_app.modules.learning.services.progress_service import ProgressService
from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
from mindstack_app.modules.learning.services.daily_stats_service import DailyStatsService

class LearningInterface:
    """Public Facade for Learning Module."""
    
    # === METRICS & ANALYTICS ===
    
    @staticmethod
    def get_score_breakdown(user_id):
        return LearningMetricsService.get_score_breakdown(user_id)

    @staticmethod
    def get_weekly_active_days_count(user_id):
        return LearningMetricsService.get_weekly_active_days_count(user_id)
        
    @staticmethod
    def get_leaderboard(timeframe: str = 'all_time', sort_by: str = 'total_score', limit: int = 50, viewer_user = None) -> List[Dict]:
        return LearningMetricsService.get_leaderboard(timeframe=timeframe, sort_by=sort_by, limit=limit, viewer_user=viewer_user)

    @staticmethod
    def get_user_learning_summary(user_id: int) -> Dict[str, Any]:
        """Get high-level summary for dashboard."""
        return LearningMetricsService.get_user_learning_summary(user_id)

    @staticmethod
    def get_daily_summary(user_id: int) -> Dict[str, Any]:
        """Get daily stats summary."""
        return DailyStatsService.get_summary(user_id)

    @staticmethod
    def get_recent_activity(user_id: int, limit: int = 6) -> List[Dict[str, Any]]:
        return LearningMetricsService.get_recent_activity(user_id, limit)
    
    @staticmethod
    def get_recent_sessions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        return LearningMetricsService.get_recent_sessions(user_id, limit)

    # === EVALUATION ===
    
    @staticmethod
    def evaluate_text_submission(submission: str, solution: str, tolerance: float = 0.0) -> Dict[str, Any]:
        """
        Evaluate a text submission against a solution.
        Returns dict with keys: is_correct, score, ratio, diff.
        """
        return compare_text(submission, solution, tolerance)

    @staticmethod
    def evaluate_mcq_submission(submission: str, correct_option: str) -> Dict[str, Any]:
        """
        Evaluate a multiple-choice submission (e.g. 'A' vs 'A').
        Returns dict with keys: is_correct, score.
        """
        return evaluate_multiple_choice(submission, correct_option)

    # === PROGRESS ===

    @staticmethod
    def get_course_progress(user_id: int, container_id: int) -> Dict[str, Any]:
        """
        Get high-level progress statistics for a course/container.
        Delegates to ProgressService to calculate completion rates.
        """
        return ProgressService.get_container_stats(user_id, container_id)

    @staticmethod
    def mark_course_completed(user_id: int, container_id: int) -> bool:
        """
        Explicitly mark a course as completed (if applicable).
        """
        return False

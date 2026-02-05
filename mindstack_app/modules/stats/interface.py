from datetime import date, datetime
from typing import Optional, List, Dict, Any
from .schemas import MetricDTO, DailyStatDTO, UserLearningSummaryDTO, LeaderboardEntryDTO
from .services.metrics import get_score_trend_series, get_activity_breakdown
from .services.analytics_service import AnalyticsService

def record_activity(user_id: int, activity_type: str, value: float = 1.0, timestamp: Optional[datetime] = None):
    """
    Public API to record user activity/metrics.
    Implementation should handle both UserMetric (global) and DailyStat (temporal).
    """
    from .services.metrics_kernel import MetricsKernel
    MetricsKernel.record_metric(user_id, activity_type, value, timestamp)

def get_user_summary(user_id: int) -> UserLearningSummaryDTO:
    """
    Get comprehensive learning summary for a user.
    """
    # This would call high-level service logic
    # For now, placeholder mapping from AnalyticsService
    data = AnalyticsService.get_dashboard_overview(user_id)
    
    # Map to DTO... (simplified for now)
    return data

def get_leaderboard(
    timeframe: str = 'all_time', 
    sort_by: str = 'total_score',
    limit: int = 50,
    viewer_user_id: Optional[int] = None
) -> List[LeaderboardEntryDTO]:
    """
    Get leaderboard data.
    """
    from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
    from mindstack_app.models import User
    
    viewer = User.query.get(viewer_user_id) if viewer_user_id else None
    
    raw_data = LearningMetricsService.get_leaderboard(
        sort_by=sort_by,
        timeframe=timeframe,
        viewer_user=viewer
    )
    
    # Convert to DTOs
    return raw_data

def get_dashboard_activity(user_id: int) -> Dict[str, Any]:
    """
    Get daily activity & score metrics for dashboard.
    Aggregates data from LearningMetricsService.
    """
    from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
    
    # 1. Today's counts
    todays_counts = LearningMetricsService.get_todays_activity_counts(user_id)
    
    # 2. Score breakdown
    score_data = LearningMetricsService.get_score_breakdown(user_id)
    
    # 3. Active days
    weekly_active_days = LearningMetricsService.get_weekly_active_days_count(user_id)
    
    # 4. Summaries (If needed for shortcut actions, though dashboard_service does it too)
    summaries = LearningMetricsService.get_user_learning_summary(user_id)

    return {
        'todays_counts': todays_counts,
        'score_data': score_data,
        'active_days': weekly_active_days,
        'summaries': summaries
    }

class StatsInterface:
    @staticmethod
    def record_activity(user_id: int, activity_type: str, value: float = 1.0, timestamp: Optional[datetime] = None):
        return record_activity(user_id, activity_type, value, timestamp)

    @staticmethod
    def get_user_summary(user_id: int) -> UserLearningSummaryDTO:
        return get_user_summary(user_id)

    @staticmethod
    def get_leaderboard(timeframe: str = 'all_time', sort_by: str = 'total_score', limit: int = 50, viewer_user_id: Optional[int] = None):
        return get_leaderboard(timeframe, sort_by, limit, viewer_user_id)

    @staticmethod
    def get_dashboard_activity(user_id: int) -> Dict[str, Any]:
        return get_dashboard_activity(user_id)

    @staticmethod
    def get_vocab_item_stats(user_id: int, item_id: int) -> dict:
        """Get detailed statistics for a vocabulary item."""
        from .services.vocabulary_stats_service import VocabularyStatsService
        return VocabularyStatsService.get_item_stats(user_id, item_id)

    @staticmethod
    def get_vocab_set_overview_stats(user_id: int, set_id: int, page: int = 1, per_page: int = 12, sort_by: str = 'default') -> dict:
        """Get overview statistics for a vocabulary set."""
        from .services.vocabulary_stats_service import VocabularyStatsService
        return VocabularyStatsService.get_course_overview_stats(user_id, set_id, page, per_page, sort_by=sort_by)

    @staticmethod
    def get_global_stats(user_id: int) -> dict:
        """Get global vocabulary statistics."""
        from .services.vocabulary_stats_service import VocabularyStatsService
        return VocabularyStatsService.get_global_stats(user_id)

    @staticmethod
    def get_full_stats(user_id: int, container_id: int) -> dict:
        """Get full statistics for a container."""
        from .services.vocabulary_stats_service import VocabularyStatsService
        return VocabularyStatsService.get_full_stats(user_id, container_id)

    @staticmethod
    def get_chart_data(user_id: int, container_id: int) -> dict:
        """Get chart data for a container."""
        from .services.vocabulary_stats_service import VocabularyStatsService
        return VocabularyStatsService.get_chart_data(user_id, container_id)

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

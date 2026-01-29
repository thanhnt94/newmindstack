"""
Metrics Kernel Service
Low-level CRUD operations for statistical models (UserMetric, DailyStat).
Provides the 'write' layer for the Analytics system.
"""
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any

from ..models import db, UserMetric, DailyStat, Achievement

class MetricsKernel:
    """
    Kernel service for managing statistical data.
    """

    @staticmethod
    def increment_user_metric(user_id: int, key: str, value: float = 1.0) -> UserMetric:
        """Increment (or create) a global user metric."""
        metric = UserMetric.query.get((user_id, key))
        if not metric:
            metric = UserMetric(user_id=user_id, metric_key=key, metric_value=0.0)
            db.session.add(metric)
        
        metric.metric_value += value
        # updated_at handles itself via onupdate or we can force it if needed
        return metric

    @staticmethod
    def set_user_metric(user_id: int, key: str, value: float) -> UserMetric:
        """Set a global user metric to a specific value (e.g. max streak)."""
        metric = UserMetric.query.get((user_id, key))
        if not metric:
            metric = UserMetric(user_id=user_id, metric_key=key, metric_value=value)
            db.session.add(metric)
        else:
            metric.metric_value = value
        return metric

    @staticmethod
    def increment_daily_stat(user_id: int, key: str, value: float = 1.0, date_obj: Optional[date] = None) -> DailyStat:
        """Increment (or create) a daily stat."""
        if not date_obj:
            date_obj = datetime.now(timezone.utc).date()
            
        stat = DailyStat.query.filter_by(user_id=user_id, date=date_obj, metric_key=key).first()
        if not stat:
            stat = DailyStat(user_id=user_id, date=date_obj, metric_key=key, metric_value=0.0)
            db.session.add(stat)
            
        stat.metric_value += value
        return stat

    @staticmethod
    def get_user_metrics(user_id: int) -> Dict[str, float]:
        """Get all global metrics for a user as a dict."""
        metrics = UserMetric.query.filter_by(user_id=user_id).all()
        return {m.metric_key: m.metric_value for m in metrics}

    @staticmethod
    def get_daily_stats_range(user_id: int, start_date: date, end_date: date) -> List[DailyStat]:
        """Get daily stats within a date range."""
        return DailyStat.query.filter(
            DailyStat.user_id == user_id,
            DailyStat.date >= start_date,
            DailyStat.date <= end_date
        ).order_by(DailyStat.date).all()
    
    @staticmethod
    def record_achievement(user_id: int, code: str, data: Optional[Dict] = None) -> Optional[Achievement]:
        """Record an achievement if it doesn't already exist."""
        exists = Achievement.query.filter_by(user_id=user_id, achievement_code=code).first()
        if exists:
            return None
            
        ach = Achievement(user_id=user_id, achievement_code=code, data=data)
        db.session.add(ach)
        return ach

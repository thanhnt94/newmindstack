from datetime import datetime
from typing import Dict, Any, Optional, List, Type
from .services.history_recorder import HistoryRecorder
from .services.history_query_service import HistoryQueryService

class LearningHistoryInterface:
    """
    Public Gateway primarily for recording and querying study history.
    Enforces Domain Isolation by preventing direct model access.
    """

    @staticmethod
    def get_log(log_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single study log as a dictionary (DTO)."""
        return HistoryQueryService.get_log(log_id)

    @staticmethod
    def count_mode_reps(user_id: int, item_id: int, learning_mode: str) -> int:
        """Count repetitions for a specific item in a specific mode."""
        return HistoryQueryService.count_mode_reps(user_id, item_id, learning_mode)

    @staticmethod
    def record_log(
        user_id: int,
        item_id: int,
        result_data: Dict[str, Any],
        context_data: Dict[str, Any],
        fsrs_snapshot: Optional[Dict[str, Any]] = None,
        game_snapshot: Optional[Dict[str, Any]] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ):
        """Record a new study interaction."""
        # Note: We return the log object because some legacy code might need ID, 
        # but optimally we should return a DTO or ID only.
        return HistoryRecorder.record_interaction(
            user_id, item_id, result_data, context_data, fsrs_snapshot, game_snapshot, context_snapshot
        )

    @staticmethod
    def get_logs_by_user(user_id: int, **kwargs) -> List[Dict[str, Any]]:
        """Get user logs as list of dicts."""
        return HistoryQueryService.get_logs_by_user(user_id, **kwargs)

    @staticmethod
    def get_study_stats(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get aggregated learning stats."""
        return HistoryQueryService.get_study_stats(user_id, start_date, end_date)

    @staticmethod
    def delete_user_history(user_id: int) -> int:
        """Delete all history for a user."""
        return HistoryQueryService.delete_user_history(user_id)

    @staticmethod
    def get_item_history(item_id: int) -> List[Dict[str, Any]]:
        """Get history for a specific item."""
        return HistoryQueryService.get_item_history(item_id)

    @staticmethod
    def get_model_class():
        """
        [SYSTEM USE ONLY] Returns the StudyLog model class.
        Allowed consumers: Admin, Backup.
        Strictly forbidden for business logic modules.
        """
        from .models import StudyLog
        return StudyLog

    @staticmethod
    def get_recent_containers(user_id: int, container_type: str, item_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent containers."""
        return HistoryQueryService.get_recent_containers(user_id, container_type, item_type, limit)

    @staticmethod
    def get_daily_activity_series(user_id: int, start_date: datetime, end_date: datetime, container_id: int, item_type: str) -> List[tuple]:
        """Get daily activity series."""
        return HistoryQueryService.get_daily_activity_series(user_id, start_date, end_date, container_id, item_type)

    @staticmethod
    def get_item_history(item_id: int, limit: int = 50, learning_mode: str = None) -> List[Dict[str, Any]]:
        """Get history for a specific item."""
        return HistoryQueryService.get_item_history(item_id, limit, learning_mode)

    @staticmethod
    def get_study_log_timeline(user_id: int, item_ids: List[int], start_date: datetime) -> List[Dict[str, Any]]:
        """Get timeline data for items."""
        return HistoryQueryService.get_study_log_timeline(user_id, item_ids, start_date)

    @staticmethod
    def get_user_history_for_optimization(user_id: int) -> List[Dict[str, Any]]:
        """Get history for FSRS optimization."""
        return HistoryQueryService.get_user_history_for_optimization(user_id)

    @staticmethod
    def delete_items_history(item_ids: List[int]) -> int:
        """Delete history for specific items."""
        return HistoryQueryService.delete_items_history(item_ids)

    @staticmethod
    def get_session_logs(session_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get paginated logs for a session."""
        return HistoryQueryService.get_session_logs(session_id, page, per_page)

    @staticmethod
    def get_first_review_dates(user_id: int, item_ids: List[int]) -> Dict[int, datetime]:
        """Get the earliest study timestamp for each item."""
        return HistoryQueryService.get_first_review_dates(user_id, item_ids)

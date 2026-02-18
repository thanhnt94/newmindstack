from typing import List, Dict, Any, Optional, Type
from datetime import datetime
from sqlalchemy import func
from mindstack_app.core.extensions import db
from ..models import StudyLog

class HistoryQueryService:
    """Service for querying learning history (ReadOnly logic)."""

    @staticmethod
    def get_log(log_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single study log as a dictionary."""
        log = StudyLog.query.get(log_id)
        if not log:
            return None
            
        return {
            'log_id': log.log_id,
            'user_id': log.user_id,
            'item_id': log.item_id,
            'container_id': log.container_id,
            'session_id': log.session_id,
            'timestamp': log.timestamp,
            'rating': log.rating,
            'is_correct': log.is_correct,
            'review_duration': log.review_duration,
            'learning_mode': log.learning_mode,
            'user_answer': log.user_answer,
            'gamification_snapshot': log.gamification_snapshot,
            'fsrs_snapshot': log.fsrs_snapshot,
            'context_snapshot': log.context_snapshot
        }

    @staticmethod
    def count_mode_reps(user_id: int, item_id: int, learning_mode: str) -> int:
        """Count repetitions for a specific item in a specific mode."""
        return StudyLog.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=learning_mode
        ).count()

    @staticmethod
    def get_logs_by_user(
        user_id: int, 
        limit: int = 100, 
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get logs for a user as simple dictionaries (DTOs).
        Avoiding returning Model instances to enforce isolation at the boundary.
        """
        query = StudyLog.query.filter(StudyLog.user_id == user_id)
        
        if start_date:
            query = query.filter(StudyLog.timestamp >= start_date)
        if end_date:
            query = query.filter(StudyLog.timestamp <= end_date)
            
        logs = query.order_by(StudyLog.timestamp.desc()).limit(limit).offset(offset).all()
        
        return [
            {
                'log_id': log.log_id,
                'item_id': log.item_id,
                'timestamp': log.timestamp,
                'rating': log.rating,
                'is_correct': log.is_correct,
                'mode': log.learning_mode,
                'container_id': log.container_id
            }
            for log in logs
        ]

    @staticmethod
    def get_item_history(item_id: int, limit: int = 50, learning_mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get history for a specific item."""
        query = StudyLog.query.filter_by(item_id=item_id)
        if learning_mode:
            query = query.filter_by(learning_mode=learning_mode)
            
        logs = query.order_by(StudyLog.timestamp.desc())\
            .limit(limit).all()
            
        return [
            {
                'timestamp': log.timestamp,
                'rating': log.rating,
                'is_correct': log.is_correct,
                'learning_mode': log.learning_mode,
                'review_duration': log.review_duration,
                'user_answer': log.user_answer,
                'gamification_snapshot': log.gamification_snapshot,
                'fsrs_snapshot': log.fsrs_snapshot
            }
            for log in logs
        ]

    @staticmethod
    def get_study_log_timeline(user_id: int, item_ids: List[int], start_date: datetime) -> List[Dict[str, Any]]:
        """Get timeline data for specific items."""
        logs = StudyLog.query.filter(
            StudyLog.user_id == user_id, 
            StudyLog.item_id.in_(item_ids), 
            StudyLog.timestamp >= start_date
        ).order_by(StudyLog.timestamp).all()
        
        return [
            {
                'timestamp': log.timestamp,
                'fsrs_snapshot': log.fsrs_snapshot,
                'rating': log.rating
            }
            for log in logs
        ]

    @staticmethod
    def get_user_history_for_optimization(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all history for a user, optimized for FSRS training.
        Returns lightweight DTOs.
        """
        logs = StudyLog.query.filter_by(user_id=user_id)\
            .order_by(StudyLog.item_id, StudyLog.timestamp)\
            .all()
            
        return [
            {
                'item_id': log.item_id,
                'timestamp': log.timestamp,
                'rating': log.rating,
                'fsrs_snapshot': log.fsrs_snapshot
            }
            for log in logs
        ]

    @staticmethod
    def get_study_stats(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Calculate aggregated stats for the Stats module.
        Returns: {total_reviews, correct_count, total_duration}
        """
        stats = db.session.query(
            func.count(StudyLog.log_id).label('count'),
            func.sum(StudyLog.is_correct.cast(db.Integer)).label('correct'),
            func.sum(StudyLog.review_duration).label('duration')
        ).filter(
            StudyLog.user_id == user_id,
            StudyLog.timestamp >= start_date,
            StudyLog.timestamp <= end_date
        ).first()
        
        return {
            'total_reviews': stats.count or 0,
            'correct_count': stats.correct or 0,
            'total_duration': int(stats.duration or 0)
        }

    @staticmethod
    def delete_user_history(user_id: int) -> int:
        """Delete all history for a user (Reset Account). Returns deleted count."""
        deleted_count = StudyLog.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return deleted_count

    @staticmethod
    def get_recent_containers(user_id: int, container_type: str, item_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of containers user recently interacted with."""
        from mindstack_app.models import LearningContainer, LearningItem

        query = (
            db.session.query(
                LearningContainer.container_id,
                LearningContainer.title,
                func.max(StudyLog.timestamp).label('last_activity')
            )
            .join(LearningItem, LearningItem.item_id == StudyLog.item_id)
            .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
            .filter(
                StudyLog.user_id == user_id,
                LearningContainer.container_type == container_type
            )
        )
        
        if item_type:
            query = query.filter(LearningItem.item_type == item_type)
            
        results = query.group_by(LearningContainer.container_id, LearningContainer.title)\
            .order_by(func.max(StudyLog.timestamp).desc())\
            .limit(limit).all()
            
        return [
            {'id': row.container_id, 'title': row.title}
            for row in results
        ]

    @staticmethod
    def get_daily_activity_series(
        user_id: int, 
        start_date: Optional[datetime], 
        end_date: Optional[datetime],
        container_id: int,
        item_type: str
    ) -> List[tuple]:
        """
        Get daily activity counts (timestamp, learning_mode).
        Returns list of (timestamp, learning_mode) tuples.
        """
        from mindstack_app.models import LearningItem
        
        query = (
            db.session.query(StudyLog.timestamp, StudyLog.learning_mode)
            .join(LearningItem, LearningItem.item_id == StudyLog.item_id)
            .filter(
                StudyLog.user_id == user_id,
                LearningItem.container_id == container_id,
                LearningItem.item_type == item_type
            )
        )
        
        if start_date:
            query = query.filter(StudyLog.timestamp >= start_date)
        if end_date:
            query = query.filter(StudyLog.timestamp <= end_date)
            
        return query.all()

    @staticmethod
    def delete_items_history(item_ids: List[int]) -> int:
        """Delete history for specific items (Admin/Reset)."""
        if not item_ids: return 0
        deleted_count = StudyLog.query.filter(StudyLog.item_id.in_(item_ids)).delete(synchronize_session=False)
        db.session.commit()
        return deleted_count

    @staticmethod
    def get_session_logs(session_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Get paginated logs for a specific session.
        Returns: {'items': [DTO], 'total': int, 'pages': int, 'current_page': int}
        """
        query = StudyLog.query.filter_by(session_id=session_id).order_by(StudyLog.timestamp.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        items = [
            {
                'log_id': log.log_id,
                'item_id': log.item_id,
                'timestamp': log.timestamp,
                'rating': log.rating,
                'is_correct': log.is_correct,
                'review_duration': log.review_duration,
                'learning_mode': log.learning_mode,
                'user_answer': log.user_answer,
                'gamification_snapshot': log.gamification_snapshot,
                'fsrs_snapshot': log.fsrs_snapshot
            }
            for log in pagination.items
        ]
        
        return {
            'items': items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }

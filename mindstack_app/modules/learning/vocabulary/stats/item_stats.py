# File: vocabulary/stats/item_stats.py
# Vocabulary Item Statistics Service
# Provides detailed statistics for individual learning items

from datetime import datetime
from sqlalchemy import func
from mindstack_app.models import LearningItem, ReviewLog
from mindstack_app.models.learning_progress import LearningProgress
from mindstack_app.models import db

class VocabularyItemStats:
    """
    Service for individual item statistics.
    Aggregates data from LearningProgress and ReviewLog.
    """
    
    @staticmethod
    def get_item_stats(user_id: int, item_id: int) -> dict:
        """
        Get comprehensive statistics for a single item.
        
        Args:
            user_id: The user's ID
            item_id: The item ID
            
        Returns:
            dict with item details and stats
        """
        # 1. Get Item Details
        item = LearningItem.query.get(item_id)
        if not item:
            return None
            
        content = item.content or {}
        
        # 2. Get Learning Progress (SRS State)
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=LearningProgress.MODE_FLASHCARD # Base progress is tracked on Flashcard mode mostly
        ).first()

        # 3. Get Review History (Logs)
        logs = ReviewLog.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).order_by(ReviewLog.timestamp.desc()).all()
        
        # 4. Aggregations from Logs
        total_attempts = len(logs)
        total_correct = sum(1 for log in logs if _is_log_correct(log))
        total_duration_ms = sum(log.duration_ms for log in logs if log.duration_ms)
        total_score = sum(log.score_change for log in logs if log.score_change is not None)
        
        # Mode distribution
        mode_counts = {}
        for log in logs:
            mode = log.review_type or 'unknown'
            if mode not in mode_counts:
                mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0}
            
            mode_counts[mode]['count'] += 1
            if log.duration_ms:
                mode_counts[mode]['duration'] += log.duration_ms
            if _is_log_correct(log):
                mode_counts[mode]['correct'] += 1

        # Current State
        mastery = progress.mastery if progress else 0.0
        streak = progress.correct_streak if progress else 0
        last_reviewed = progress.last_reviewed if progress else None
        next_due = progress.due_time if progress else None
        
        # Calculate derived metrics
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (total_duration_ms / total_attempts) if total_attempts > 0 else 0
        
        # Determine Status
        status = 'new'
        if progress:
            now = datetime.utcnow()
            if progress.mastery >= 0.8:
                status = 'mastered'
            elif progress.due_time and progress.due_time <= now:
                status = 'due'
            elif progress.incorrect_streak and progress.incorrect_streak >= 2:
                status = 'hard'
            else:
                status = 'learning'
                
        return {
            'item': {
                'id': item.item_id,
                'front': content.get('front', '?'),
                'back': content.get('back', '?'),
                'pronunciation': content.get('pronunciation'),
                'meaning': content.get('meaning') # Should ideally be consistent with 'back' or separate
            },
            'progress': {
                'status': status,
                'mastery': round(mastery * 100, 1),
                'streak': streak,
                'last_reviewed': last_reviewed,
                'next_due': next_due,
                'due_relative': _get_relative_time_string(next_due) if next_due else 'Chưa lên lịch',
                'ease_factor': round(progress.easiness_factor, 2) if progress else 2.5
            },
            'performance': {
                'total_reviews': total_attempts,
                'accuracy': round(accuracy, 1),
                'total_time_ms': total_duration_ms,
                'avg_time_ms': round(avg_duration, 0),
                'total_score': total_score
            },
            'modes': mode_counts,
            'history': [
                {
                    'timestamp': log.timestamp,
                    'mode': log.review_type,
                    'result': 'Correct' if _is_log_correct(log) else 'Incorrect',
                    'duration_ms': log.duration_ms,
                    'user_answer': log.user_answer
                }
                for log in logs[:50] # Limit history list
            ]
        }

def _is_log_correct(log) -> bool:
    """Determine if a review log represents a correct answer."""
    # 1. Explicit correctness (Quiz, Typing, etc.)
    if log.is_correct is not None:
        return log.is_correct
        
    # 2. Flashcard Rating (1=Again, 2=Hard, 3=Good, 4=Easy)
    # Usually rating >= 2 is considered a 'pass' in SM-2, 
    # but strictly 'correct' usually excludes 'Again'.
    if log.rating is not None:
        return log.rating >= 2
        
    return False

def _get_relative_time_string(dt: datetime) -> str:
    """Return a human readable string like 'trong 2 ngày' or 'quá hạn 5 giờ'."""
    now = datetime.utcnow()
    diff = dt - now
    total_seconds = diff.total_seconds()
    
    is_past = total_seconds < 0
    seconds = abs(int(total_seconds))
    
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    
    if is_past:
        prefix = "Quá hạn"
    else:
        prefix = "Trong"
        
    if days > 0:
        return f"{prefix} {days} ngày"
    elif hours > 0:
        return f"{prefix} {hours} giờ"
    elif minutes > 0:
        return f"{prefix} {minutes} phút"
    else:
        return "Ngay bây giờ"

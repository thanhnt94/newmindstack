# File: vocabulary/stats/item_stats.py
# Vocabulary Item Statistics Service
# Provides detailed statistics for individual learning items

from datetime import datetime
from sqlalchemy import func
from mindstack_app.models import LearningItem, ReviewLog, User, ContainerContributor, LearningContainer
from mindstack_app.models.learning_progress import LearningProgress
from flask import url_for
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
        
        # Mode distribution with detailed stats
        mode_counts = {}
        for log in logs:
            mode = log.review_type or 'unknown'
            if mode not in mode_counts:
                mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0, 'score': 0}
            
            mode_counts[mode]['count'] += 1
            if log.duration_ms:
                mode_counts[mode]['duration'] += log.duration_ms
            if _is_log_correct(log):
                mode_counts[mode]['correct'] += 1
            if log.score_change:
                mode_counts[mode]['score'] += log.score_change

        # Calculate mode-specific accuracy and average score
        for mode_data in mode_counts.values():
            mode_data['accuracy'] = round((mode_data['correct'] / mode_data['count'] * 100), 1) if mode_data['count'] > 0 else 0
            mode_data['avg_duration'] = round(mode_data['duration'] / mode_data['count'], 0) if mode_data['count'] > 0 else 0

        # Current State
        mastery = progress.mastery if progress else 0.0
        streak = progress.correct_streak if progress else 0
        last_reviewed = progress.last_reviewed if progress else None
        next_due = progress.due_time if progress else None
        
        # Calculate derived metrics
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (total_duration_ms / total_attempts) if total_attempts > 0 else 0
        avg_score = (total_score / total_attempts) if total_attempts > 0 else 0
        
        # NEW: First and Last reviewed dates
        first_reviewed = logs[-1].timestamp if logs else None
        last_reviewed_log = logs[0].timestamp if logs else None
        
        # NEW: Mastery trend (compare recent vs older)
        mastery_trend = 0
        if len(logs) >= 6:
            recent_mastery = [log.mastery_snapshot for log in logs[:3] if log.mastery_snapshot is not None]
            older_mastery = [log.mastery_snapshot for log in logs[3:6] if log.mastery_snapshot is not None]
            if recent_mastery and older_mastery:
                recent_avg = sum(recent_mastery) / len(recent_mastery)
                older_avg = sum(older_mastery) / len(older_mastery)
                mastery_trend = round((recent_avg - older_avg) * 100, 1)  # Percentage change
        
        # NEW: Rating distribution (for flashcard mode)
        rating_dist = {'again': 0, 'hard': 0, 'good': 0, 'easy': 0}
        for log in logs:
            if log.review_type == 'flashcard' and log.rating is not None:
                if log.rating <= 1:
                    rating_dist['again'] += 1
                elif log.rating == 2:
                    rating_dist['hard'] += 1
                elif log.rating == 3:
                    rating_dist['good'] += 1
                else:  # 4 or 5
                    rating_dist['easy'] += 1
        
        # NEW: Time metrics (min, max)
        durations = [log.duration_ms for log in logs if log.duration_ms and log.duration_ms > 0]
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # NEW: Review frequency
        review_frequency = 0
        if len(logs) >= 2 and first_reviewed:
            time_span_days = (logs[0].timestamp - first_reviewed).days or 1
            review_frequency = round(len(logs) / (time_span_days / 7), 1)  # Reviews per week
        
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
                
        # Determine permissions
        can_edit = False
        edit_url = ""
        user = User.query.get(user_id)
        if user:
            if user.user_role == User.ROLE_ADMIN:
                can_edit = True
            elif item.container and item.container.creator_user_id == user_id:
                can_edit = True
            else:
                contributor = ContainerContributor.query.filter_by(
                    container_id=item.container_id,
                    user_id=user_id,
                    permission_level='editor'
                ).first()
                if contributor:
                    can_edit = True
        
        if can_edit:
            edit_url = url_for('content_management.content_management_flashcards.edit_flashcard_item', 
                               set_id=item.container_id, 
                               item_id=item_id)

        # [NEW] Get User Item Markers
        from mindstack_app.models.user import UserItemMarker
        markers = UserItemMarker.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).all()
        marker_list = [m.marker_type for m in markers]

        return {
            'markers': marker_list, # [NEW]
            'item': {
                'id': item.item_id,
                'container_title': item.container.title if item.container else 'Unknown Set',
                'container_id': item.container_id,
                'front': content.get('front', '?'),
                'back': content.get('back', '?'),
                'pronunciation': content.get('pronunciation'),
                'meaning': content.get('meaning'),
                'image': content.get('image'),
                'audio': content.get('audio'),
                'example': content.get('example'),
                'example_meaning': content.get('example_meaning'),
                'phonetic': content.get('phonetic'),
                'tags': content.get('tags', []),
                'custom_data': content.get('custom_data') or content.get('custom_content', {}),  # [UPDATED] Check custom_content too
                'ai_explanation': item.ai_explanation,        # [NEW] Column in DB
                'note': (progress.mode_data or {}).get('note', '') if progress else '', # [NEW]
                'full_content': content # Pass original content for flexibility
            },
            'progress': {
                'status': status,
                'mastery': round(mastery * 100, 1),
                'streak': streak,
                'last_reviewed': last_reviewed,
                'next_due': next_due,
                'due_relative': _get_relative_time_string(next_due) if next_due else 'Chưa lên lịch',
                'ease_factor': round(progress.easiness_factor, 2) if progress else 2.5,
                'mastery_trend': mastery_trend,
                'first_reviewed': first_reviewed,
                'last_reviewed_log': last_reviewed_log,
                'last_reviewed_relative': _get_relative_time_string(last_reviewed_log) if last_reviewed_log else 'Chưa học'
            },
            'performance': {
                'total_reviews': total_attempts,
                'accuracy': round(accuracy, 1),
                'total_time_ms': total_duration_ms,
                'avg_time_ms': round(avg_duration, 0),
                'min_time_ms': min_duration,
                'max_time_ms': max_duration,
                'total_score': total_score,
                'avg_score': round(avg_score, 1),
                'review_frequency': review_frequency
            },
            'modes': mode_counts,
            'rating_distribution': rating_dist,
            'time_stats': {
                'total_ms': total_duration_ms,
                'avg_ms': round(avg_duration, 0),
                'min_ms': min_duration,
                'max_ms': max_duration
            },
            'history': [
                {
                    'timestamp': log.timestamp,
                    'mode': log.review_type,
                    'result': 'Correct' if _is_log_correct(log) else 'Incorrect',
                    'duration_ms': log.duration_ms,
                    'user_answer': log.user_answer,
                    'score_change': log.score_change,
                    'rating': log.rating,
                    'mastery_snapshot': log.mastery_snapshot
                }
                for log in logs[:50] # Limit history list
            ],
            'permissions': {
                'can_edit': can_edit,
                'edit_url': edit_url
            }
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

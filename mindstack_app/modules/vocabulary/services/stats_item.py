# File: vocabulary/stats/item_stats.py
# Vocabulary Item Statistics Service
# Provides detailed statistics for individual learning items

from datetime import datetime
from sqlalchemy import func
from mindstack_app.models import LearningItem, ReviewLog, User, ContainerContributor, LearningContainer, UserItemMarker
from mindstack_app.modules.learning.models import LearningProgress
from mindstack_app.utils.content_renderer import render_text_field
from flask import url_for
from mindstack_app.models import db
from mindstack_app.modules.learning.services.fsrs_service import FsrsService

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
        total_duration_ms = sum(log.review_duration for log in logs if log.review_duration)
        total_score = sum(log.score_change for log in logs if log.score_change is not None)
        
        # Mode distribution with detailed stats
        mode_counts = {}
        for log in logs:
            mode = log.review_type or 'unknown'
            if mode not in mode_counts:
                mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0, 'score': 0}
            
            mode_counts[mode]['count'] += 1
            if log.review_duration:
                mode_counts[mode]['duration'] += log.review_duration
            if _is_log_correct(log):
                mode_counts[mode]['correct'] += 1
            if log.score_change:
                mode_counts[mode]['score'] += log.score_change

        # Calculate mode-specific accuracy and average score
        for mode_data in mode_counts.values():
            mode_data['accuracy'] = round((mode_data['correct'] / mode_data['count'] * 100), 1) if mode_data['count'] > 0 else 0
            mode_data['avg_duration'] = round(mode_data['duration'] / mode_data['count'], 0) if mode_data['count'] > 0 else 0

        # Current State
        stability = progress.fsrs_stability if progress else 0.0
        difficulty = progress.fsrs_difficulty if progress else 0.0
        state = progress.fsrs_state if progress else 0
        retrievability = FsrsService.get_retrievability(progress) if progress else 0.0
        streak = progress.correct_streak if progress else 0
        last_reviewed = progress.fsrs_last_review if progress else None
        next_due = progress.fsrs_due if progress else None
        
        # Calculate derived metrics
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (total_duration_ms / total_attempts) if total_attempts > 0 else 0
        avg_score = (total_score / total_attempts) if total_attempts > 0 else 0
        
        # NEW: First and Last reviewed dates
        first_reviewed = logs[-1].timestamp if logs else None
        last_reviewed_log = logs[0].timestamp if logs else None
        
        # NEW: Stability trend (compare recent vs older)
        stability_trend = 0
        if len(logs) >= 6:
            recent_stability = [log.fsrs_stability for log in logs[:3] if log.fsrs_stability is not None]
            older_stability = [log.fsrs_stability for log in logs[3:6] if log.fsrs_stability is not None]
            if recent_stability and older_stability:
                recent_avg = sum(recent_stability) / len(recent_stability)
                older_avg = sum(older_stability) / len(older_stability)
                stability_trend = round(recent_avg - older_avg, 1)  # Absolute day change
        
        # NEW: Rating distribution (for strict FSRS 1-4 ratings)
        rating_dist = {'again': 0, 'hard': 0, 'good': 0, 'easy': 0}
        for log in logs:
            if log.review_type == 'flashcard' and log.rating is not None:
                if log.rating <= 1:
                    rating_dist['again'] += 1
                elif log.rating == 2:
                    rating_dist['hard'] += 1
                elif log.rating == 3:
                    rating_dist['good'] += 1
                else: # 4 (Easy)
                    rating_dist['easy'] += 1
        
        # NEW: Time metrics (min, max)
        durations = [log.review_duration for log in logs if log.review_duration and log.review_duration > 0]
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # NEW: Review frequency
        review_frequency = 0
        if len(logs) >= 2 and first_reviewed:
            time_span_days = (logs[0].timestamp - first_reviewed).days or 1
            review_frequency = round(len(logs) / (time_span_days / 7), 1)  # Reviews per week
        
        # Determine Status using HardItemService
        status = 'new'
        if progress:
            now = datetime.utcnow()
            
            # Use centralized HardItemService
            from mindstack_app.modules.learning.services.hard_item_service import HardItemService
            
            if stability >= 21.0:
                status = 'mastered'
            elif progress.fsrs_due and progress.fsrs_due <= now:
                status = 'due'
            elif HardItemService.is_hard_item(user_id, item_id):
                status = 'hard'
            else:
                status = 'learning'
                
        # Determine permissions
        can_edit = False
        edit_url = ""
        user_obj = User.query.get(user_id)
        if user_obj:
            if user_obj.user_role == User.ROLE_ADMIN:
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
            edit_url = url_for('content_management.edit_flashcard_item', 
                               set_id=item.container_id, 
                               item_id=item_id,
                               is_modal='true')

        # [NEW] Get User Item Markers
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
                # BBCode rendering for text content fields
                'front': render_text_field(content.get('front', '?')),
                'back': render_text_field(content.get('back', '?')),
                'pronunciation': content.get('pronunciation'),
                'meaning': render_text_field(content.get('meaning')),
                'image': content.get('image'),
                'audio': content.get('audio'),
                'example': render_text_field(content.get('example')),
                'example_meaning': render_text_field(content.get('example_meaning')),
                'phonetic': content.get('phonetic'),
                'tags': content.get('tags', []),
                'custom_data': content.get('custom_data') or content.get('custom_content', {}),  # [UPDATED] Check custom_content too
                'ai_explanation': render_text_field(item.ai_explanation),        # [NEW] BBCode rendered
                'note': (progress.mode_data or {}).get('note', '') if progress else '', # [NEW]
                'full_content': content # Pass original content for flexibility
            },
            'progress': {
                'status': status,
                'retrievability': round(retrievability * 100, 1),
                'streak': streak,
                'ease_factor': round(difficulty, 2),
                'due_relative': _get_relative_time_string(next_due) if next_due else 'Sẵn sàng',
                'stability_trend': stability_trend,
                'mastery_trend': stability_trend, # Template uses mastery_trend for stability change
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
                    'duration_ms': log.review_duration,
                    'user_answer': log.user_answer,
                    'score_change': log.score_change,
                    'rating': log.rating,
                    'stability_snapshot': round(log.fsrs_stability or 0, 2),
                    'difficulty_snapshot': round(log.fsrs_difficulty or 0, 2)
                }
                for log in logs[:50] # Limit history list
            ],
            'permissions': {
                'can_edit': can_edit,
                'edit_url': edit_url
            }
        }

def _get_state_name(state: int) -> str:
    """Map state integer to human readable name."""
    names = {
        0: 'New',
        1: 'Learning',
        2: 'Review',
        3: 'Relearning'
    }
    return names.get(state, 'Unknown')


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

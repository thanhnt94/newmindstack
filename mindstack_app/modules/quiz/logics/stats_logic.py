# File: mindstack_app/modules/learning/quiz_learning/quiz_stats_logic.py
# Phiên bản: 3.1
# MỤC ĐÍCH: Cập nhật để đọc từ StudyLog table thay vì ReviewLog.

from mindstack_app.modules.learning_history.models import StudyLog
from mindstack_app.modules.learning.models import LearningProgress
import datetime

def get_quiz_item_statistics(user_id, item_id):
    """
    Lấy các thống kê chi tiết về tiến độ của người dùng đối với một câu hỏi Quiz cụ thể.
    """
    progress = LearningProgress.query.filter_by(
        user_id=user_id, 
        item_id=item_id,
        learning_mode='quiz' # or LearningProgress.MODE_QUIZ if imported constant
    ).first()

    if not progress:
        return None

    total_attempts = (progress.times_correct or 0) + (progress.times_incorrect or 0)
    correct_percentage = (progress.times_correct or 0) / total_attempts * 100 if total_attempts > 0 else 0

    # Query StudyLog table
    logs = StudyLog.query.filter_by(
        user_id=user_id, item_id=item_id, learning_mode='quiz'
    ).order_by(StudyLog.timestamp.desc()).all()
    
    formatted_review_history = []
    for log in logs:
        fsrs = log.fsrs_snapshot or {}
        gamification = log.gamification_snapshot or {}
        
        entry = {
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'timestamp_formatted': log.timestamp.strftime("%H:%M %d/%m/%Y") if log.timestamp else None,
            'user_answer': log.user_answer,
            'is_correct': log.is_correct,
            'score_change': gamification.get('score_change', 0),
            'stability': fsrs.get('stability'),
            'duration_ms': log.review_duration
        }
        formatted_review_history.append(entry)

    return {
        'total_attempts': total_attempts,
        'times_correct': progress.times_correct or 0,
        'times_incorrect': progress.times_incorrect or 0,
        'correct_percentage': round(correct_percentage, 2),
        'correct_streak': progress.correct_streak or 0,
        'incorrect_streak': progress.incorrect_streak or 0,
        'status': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(progress.fsrs_state, 'new'),
        'first_seen': progress.first_seen.isoformat() if progress.first_seen else None,
        'last_reviewed': progress.fsrs_last_review.isoformat() if progress.fsrs_last_review else None,
        'review_history': formatted_review_history
    }
# File: mindstack_app/modules/learning/quiz_learning/quiz_stats_logic.py
# Phiên bản: 3.2
# MỤC ĐÍCH: Cập nhật để đọc từ StudyLog và ItemMemoryState.

# REFAC: StudyLog import removed (Isolation)
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface
import datetime

def get_quiz_item_statistics(user_id, item_id):
    """
    Lấy các thống kê chi tiết về tiến độ của người dùng đối với một câu hỏi Quiz cụ thể.
    """
    state_record = FSRSInterface.get_item_state(user_id, item_id)

    if not state_record:
        return None

    times_correct = state_record.times_correct or 0
    times_incorrect = state_record.times_incorrect or 0
    total_attempts = times_correct + times_incorrect
    correct_percentage = times_correct / total_attempts * 100 if total_attempts > 0 else 0

    # Query via LearningHistoryInterface
    from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
    logs = LearningHistoryInterface.get_item_history(item_id, limit=100, learning_mode='quiz')
    
    formatted_review_history = []
    for log in logs:
        fsrs = log.get('fsrs_snapshot') or {}
        gamification = log.get('gamification_snapshot') or {}
        timestamp = log.get('timestamp')
        
        entry = {
            'timestamp': timestamp.isoformat() if timestamp else None,
            'timestamp_formatted': timestamp.strftime("%H:%M %d/%m/%Y") if timestamp else None,
            'user_answer': log.get('user_answer'),
            'is_correct': log.get('is_correct'),
            'score_change': gamification.get('score_change', 0),
            'stability': fsrs.get('stability'),
            'duration_ms': log.get('review_duration')
        }
        formatted_review_history.append(entry)

    return {
        'total_attempts': total_attempts,
        'times_correct': times_correct,
        'times_incorrect': times_incorrect,
        'correct_percentage': round(correct_percentage, 2),
        'correct_streak': state_record.streak or 0,
        'incorrect_streak': 0, # Not tracked in ItemMemoryState core, maybe add to data if needed
        'status': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(state_record.state, 'new'),
        'first_seen': state_record.created_at.isoformat() if state_record.created_at else None,
        'last_reviewed': state_record.last_review.isoformat() if state_record.last_review else None,
        'review_history': formatted_review_history
    }

# File: mindstack_app/modules/learning/quiz_learning/quiz_stats_logic.py
# Phiên bản: 3.0
# MỤC ĐÍCH: Cập nhật để đọc từ ReviewLog table thay vì JSON review_history.

from mindstack_app.models import QuizProgress, ReviewLog
import datetime

def get_quiz_item_statistics(user_id, item_id):
    """
    Lấy các thống kê chi tiết về tiến độ của người dùng đối với một câu hỏi Quiz cụ thể.
    Truy vấn từ model QuizProgress và ReviewLog.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của câu hỏi Quiz.

    Returns:
        dict: Một dictionary chứa các thống kê, hoặc None nếu không tìm thấy QuizProgress.
    """
    progress = QuizProgress.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not progress:
        return None

    total_attempts = (progress.times_correct or 0) + (progress.times_incorrect or 0)
    correct_percentage = (progress.times_correct or 0) / total_attempts * 100 if total_attempts > 0 else 0

    # Query ReviewLog table instead of JSON review_history
    logs = ReviewLog.query.filter_by(
        user_id=user_id, item_id=item_id, review_type='quiz'
    ).order_by(ReviewLog.timestamp.desc()).all()
    
    formatted_review_history = []
    for log in logs:
        entry = {
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'timestamp_formatted': log.timestamp.strftime("%H:%M %d/%m/%Y") if log.timestamp else None,
            'user_answer': log.user_answer,
            'is_correct': log.is_correct,
            'score_change': log.score_change
        }
        formatted_review_history.append(entry)

    return {
        'total_attempts': total_attempts,
        'times_correct': progress.times_correct or 0,
        'times_incorrect': progress.times_incorrect or 0,
        'correct_percentage': round(correct_percentage, 2),
        'correct_streak': progress.correct_streak or 0,
        'incorrect_streak': progress.incorrect_streak or 0,
        'status': progress.status,
        'first_seen': progress.first_seen_timestamp.isoformat() if progress.first_seen_timestamp else None,
        'last_reviewed': progress.last_reviewed.isoformat() if progress.last_reviewed else None,
        'review_history': formatted_review_history
    }
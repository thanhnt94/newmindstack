# File: mindstack_app/modules/learning/flashcard_learning/flashcard_stats_logic.py
# Phiên bản: 2.1
# MỤC ĐÍCH: Cập nhật logic thống kê để phản ánh đầy đủ các chỉ số của SM-2.
# ĐÃ SỬA: Thay đổi cách tính correct_rate, hard_count và thêm các chỉ số SM-2.

from ....models import db, FlashcardProgress
import datetime

def get_flashcard_item_statistics(user_id, item_id):
    """
    Truy vấn và tính toán các thống kê chi tiết cho một flashcard cụ thể của người dùng.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của flashcard.

    Returns:
        dict: Một dictionary chứa các thống kê của flashcard.
    """
    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not progress or not progress.review_history:
        return {
            'times_reviewed': 0,
            'correct_count': 0,
            'incorrect_count': 0,
            'vague_count': 0, # ĐÃ SỬA: Đổi hard_count thành vague_count
            'correct_rate': 0.0,
            'current_streak': 0,
            'longest_streak': 0,
            'first_seen': None,
            'last_reviewed': None,
            'next_review': None,
            'easiness_factor': 2.5,
            'repetitions': 0,
            'interval': 0,
            'status': 'new'
        }

    total_reviews = len(progress.review_history)
    correct_count = 0
    incorrect_count = 0
    vague_count = 0 # ĐÃ SỬA: Đổi hard_count thành vague_count
    current_streak = 0
    longest_streak = 0
    
    # Tính toán các thống kê dựa trên review_history
    for review in progress.review_history:
        quality = review.get('user_answer_quality', 0)
        
        # SỬA: Logic tính các chỉ số dựa trên SM-2
        # Quality 3, 4, 5 được coi là đúng
        if quality >= 3:
            correct_count += 1
            current_streak += 1
        else:
            incorrect_count += 1
            if current_streak > longest_streak:
                longest_streak = current_streak
            current_streak = 0
        
        # Quality 2 được coi là mơ hồ
        if quality == 2:
            vague_count += 1 # ĐÃ SỬA: Đếm số lần trả lời mơ hồ

    # Cập nhật longest_streak cuối cùng
    if current_streak > longest_streak:
        longest_streak = current_streak

    # SỬA: Tỉ lệ đúng được tính dựa trên số lần đúng so với tổng số lần trả lời
    correct_rate = (correct_count / total_reviews) * 100 if total_reviews > 0 else 0.0

    stats = {
        'times_reviewed': total_reviews,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'vague_count': vague_count, # ĐÃ SỬA: Trả về vague_count
        'correct_rate': round(correct_rate, 2),
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'first_seen': progress.first_seen_timestamp.isoformat() if progress.first_seen_timestamp else None,
        'last_reviewed': progress.last_reviewed.isoformat() if progress.last_reviewed else None,
        'next_review': progress.due_time.isoformat() if progress.due_time else None,
        'easiness_factor': round(progress.easiness_factor, 2),
        'repetitions': progress.repetitions,
        'interval': progress.interval,
        'status': progress.status
    }
    return stats
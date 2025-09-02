# File: mindstack_app/modules/learning/flashcard_learning/flashcard_stats_logic.py
# Phiên bản: 1.1
# Mục đích: Chứa logic để tính toán và trả về các thống kê chi tiết cho từng thẻ Flashcard.
# ĐÃ SỬA: Cập nhật hàm get_flashcard_item_statistics để tính toán các chỉ số
#         thống kê (total_reviews, times_correct, streak, v.v.) bằng cách phân tích
#         dữ liệu từ cột JSON review_history.

from ....models import UserProgress
import datetime

def get_flashcard_item_statistics(user_id, item_id):
    """
    Lấy các thống kê chi tiết về tiến độ của người dùng đối với một thẻ Flashcard cụ thể.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của thẻ Flashcard.

    Returns:
        dict: Một dictionary chứa các thống kê, hoặc None nếu không tìm thấy UserProgress.
              Các thống kê bao gồm:
              - 'total_reviews': Tổng số lần ôn tập.
              - 'times_correct': Số lần trả lời đúng (tự đánh giá >= 3).
              - 'times_incorrect': Số lần trả lời sai (tự đánh giá <= 1).
              - 'times_vague': Số lần trả lời mập mờ (tự đánh giá = 2).
              - 'correct_percentage': Tỷ lệ trả lời đúng (%).
              - 'correct_streak': Chuỗi đúng liên tiếp hiện tại.
              - 'incorrect_streak': Chuỗi sai liên tiếp hiện tại.
              - 'vague_streak': Chuỗi mập mờ liên tiếp hiện tại.
              - 'status': Trạng thái học tập ('new', 'learning', 'mastered', 'hard').
              - 'first_seen': Thời điểm nhìn thấy lần đầu (định dạng ISO 8601).
              - 'last_reviewed': Thời điểm ôn tập cuối cùng (định dạng ISO 8601).
              - 'due_time': Thời điểm ôn tập tiếp theo (định dạng ISO 8601).
              - 'review_history': Lịch sử trả lời đầy đủ (danh sách các dict).
    """
    progress = UserProgress.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not progress:
        return None # Không có tiến độ cho thẻ này

    total_reviews = 0
    times_correct = 0
    times_incorrect = 0
    times_vague = 0
    
    correct_streak = 0
    incorrect_streak = 0
    vague_streak = 0
    
    # Phân tích review_history để tính toán lại các chỉ số đã bị xóa
    formatted_review_history = []
    if progress.review_history:
        for entry in progress.review_history:
            total_reviews += 1
            quality = entry.get('user_answer_quality', 0)
            is_correct = entry.get('is_correct', False)

            if is_correct:
                times_correct += 1
                incorrect_streak = 0
                vague_streak = 0
                correct_streak += 1
            elif quality == 2:
                times_vague += 1
                correct_streak = 0
                incorrect_streak = 0
                vague_streak += 1
            else:
                times_incorrect += 1
                correct_streak = 0
                vague_streak = 0
                incorrect_streak += 1
            
            # Định dạng lại timestamp cho mỗi entry
            if isinstance(entry.get('timestamp'), str):
                try:
                    dt_object = datetime.datetime.fromisoformat(entry['timestamp'])
                    entry['timestamp_formatted'] = dt_object.strftime("%H:%M %d/%m/%Y")
                except ValueError:
                    entry['timestamp_formatted'] = entry['timestamp']
            else:
                entry['timestamp_formatted'] = None
            formatted_review_history.append(entry)

    correct_percentage = (times_correct / total_reviews * 100) if total_reviews > 0 else 0

    return {
        'total_reviews': total_reviews,
        'times_correct': times_correct,
        'times_incorrect': times_incorrect,
        'times_vague': times_vague,
        'correct_percentage': round(correct_percentage, 2),
        'correct_streak': correct_streak,
        'incorrect_streak': incorrect_streak,
        'vague_streak': vague_streak,
        'status': progress.status,
        'first_seen': progress.first_seen_timestamp.isoformat() if progress.first_seen_timestamp else None,
        'last_reviewed': progress.last_reviewed.isoformat() if progress.last_reviewed else None,
        'due_time': progress.due_time.isoformat() if progress.due_time else None,
        'review_history': formatted_review_history
    }
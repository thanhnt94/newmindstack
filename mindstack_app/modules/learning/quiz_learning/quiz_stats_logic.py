# File: mindstack_app/modules/learning/quiz_learning/quiz_stats_logic.py
# Phiên bản: 1.1
# Mục đích: Chứa logic để tính toán và trả về các thống kê chi tiết cho từng câu hỏi Quiz.
# ĐÃ SỬA: Điều chỉnh để trả về review_history chi tiết hơn thay vì chỉ tóm tắt.
# ĐÃ SỬA: Định dạng lại ngày tháng để dễ sử dụng hơn ở frontend.

from ....models import UserProgress
import datetime

def get_quiz_item_statistics(user_id, item_id):
    """
    Lấy các thống kê chi tiết về tiến độ của người dùng đối với một câu hỏi Quiz cụ thể.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của câu hỏi Quiz.

    Returns:
        dict: Một dictionary chứa các thống kê, hoặc None nếu không tìm thấy UserProgress.
              Các thống kê bao gồm:
              - 'total_attempts': Tổng số lần trả lời.
              - 'times_correct': Số lần trả lời đúng.
              - 'times_incorrect': Số lần trả lời sai.
              - 'correct_percentage': Tỷ lệ trả lời đúng (%).
              - 'correct_streak': Chuỗi đúng liên tiếp hiện tại.
              - 'incorrect_streak': Chuỗi sai liên tiếp hiện tại.
              - 'status': Trạng thái học tập ('new', 'learning', 'mastered', 'hard').
              - 'first_seen': Thời điểm nhìn thấy lần đầu (định dạng ISO 8601).
              - 'last_reviewed': Thời điểm ôn tập cuối cùng (định dạng ISO 8601).
              - 'review_history': Lịch sử trả lời đầy đủ (danh sách các dict).
    """
    progress = UserProgress.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not progress:
        return None # Không có tiến độ cho câu hỏi này

    total_attempts = (progress.times_correct or 0) + (progress.times_incorrect or 0)
    correct_percentage = (progress.times_correct or 0) / total_attempts * 100 if total_attempts > 0 else 0

    # Lấy review_history và định dạng lại timestamp nếu có
    formatted_review_history = []
    if progress.review_history:
        for entry in progress.review_history:
            # Chuyển đổi chuỗi ISO 8601 thành đối tượng datetime rồi định dạng lại
            if isinstance(entry.get('timestamp'), str):
                try:
                    dt_object = datetime.datetime.fromisoformat(entry['timestamp'])
                    entry['timestamp_formatted'] = dt_object.strftime("%H:%M %d/%m/%Y")
                except ValueError:
                    entry['timestamp_formatted'] = entry['timestamp'] # Giữ nguyên nếu lỗi định dạng
            else:
                entry['timestamp_formatted'] = None # Hoặc xử lý theo cách khác nếu timestamp không phải chuỗi
            formatted_review_history.append(entry)

    return {
        'total_attempts': total_attempts,
        'times_correct': progress.times_correct or 0,
        'times_incorrect': progress.times_incorrect or 0,
        'correct_percentage': round(correct_percentage, 2), # Làm tròn 2 chữ số thập phân
        'correct_streak': progress.correct_streak or 0,
        'incorrect_streak': progress.incorrect_streak or 0,
        'status': progress.status,
        'first_seen': progress.first_seen_timestamp.isoformat() if progress.first_seen_timestamp else None,
        'last_reviewed': progress.last_reviewed.isoformat() if progress.last_reviewed else None,
        'review_history': formatted_review_history # Trả về lịch sử đầy đủ
    }


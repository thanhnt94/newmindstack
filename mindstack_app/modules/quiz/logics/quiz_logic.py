# File: mindstack_app/modules/learning/quiz_learning/quiz_logic.py
# Phiên bản: 3.0
# MỤC ĐÍCH: Cập nhật logic để sử dụng model LearningProgress (unified).
# ĐÃ SỬA: Thay thế import QuizProgress bằng LearningProgress.
# ĐÃ SỬA: Cập nhật logic truy vấn và tạo bản ghi với learning_mode='quiz'.
# ĐÃ SỬA: Thêm item_type vào ScoreLog khi tạo bản ghi.

from mindstack_app.models import LearningItem, User, db
from mindstack_app.modules.learning.models import LearningProgress
from mindstack_app.modules.gamification.services.scoring_service import ScoreService
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app # Import current_app
def _get_score_value(key: str, default: int) -> int:
    """Fetch an integer score value from runtime config with fallback."""
    from mindstack_app.services.config_service import get_runtime_config
    raw_value = get_runtime_config(key, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default

def process_quiz_answer(user_id, item_id, user_answer_text, current_user_total_score,
                        session_id=None, container_id=None, mode=None):
    """
    Xử lý một câu trả lời Quiz của người dùng, cập nhật QuizProgress,
    tính điểm và ghi log điểm số.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của câu hỏi Quiz.
        user_answer_text (str): Đáp án mà người dùng đã chọn (ký tự lựa chọn: 'A', 'B', 'C', 'D').
        current_user_total_score (int): Tổng điểm hiện tại của người dùng trước khi xử lý câu này.
        session_id (int): ID của phiên học để lưu context.
        container_id (int): ID của container/bộ học.
        mode (str): Chế độ học (new, review, difficult, etc.).

    Returns:
        tuple: (score_change, updated_total_score, is_correct, correct_option_char, explanation)
               score_change (int): Điểm số thay đổi trong lần này.
               updated_total_score (int): Tổng điểm mới của người dùng.
               is_correct (bool): True nếu câu trả lời đúng, False nếu sai.
               correct_option_char (str): Ký tự của đáp án đúng (ví dụ: 'A', 'B').
               explanation (str): Giải thích cho câu trả lời.
    """
    score_change = 0
    is_first_time = False

    # Lấy thông tin câu hỏi
    item = LearningItem.query.get(item_id)
    if not item:
        # Xử lý trường hợp không tìm thấy item (lỗi hiếm gặp nếu luồng bình thường)
        return 0, current_user_total_score, False, None, "Lỗi: Không tìm thấy câu hỏi."

    # Lấy đáp án đúng (dạng văn bản) và các lựa chọn
    correct_answer_text_from_db = item.content.get('correct_answer')
    options = item.content.get('options', {})
    explanation = item.content.get('explanation') or item.ai_explanation # Ưu tiên giải thích thủ công

    # XÁC ĐỊNH KÝ TỰ CỦA ĐÁP ÁN ĐÚNG DỰA TRÊN NỘI DUNG VĂN BẢN
    correct_option_char = None
    for key, value in options.items():
        if value == correct_answer_text_from_db:
            correct_option_char = key
            break
    
    if correct_option_char is None:
        if correct_answer_text_from_db in ['A', 'B', 'C', 'D']:
             correct_option_char = correct_answer_text_from_db
        else:
            current_app.logger.error(f"Lỗi dữ liệu: Không tìm thấy ký tự lựa chọn cho đáp án đúng '{correct_answer_text_from_db}' của item_id={item_id}. Options: {options}")
            is_correct = False
            return score_change, current_user_total_score, is_correct, correct_option_char, explanation

    is_correct = (user_answer_text == correct_option_char)

    # 1. Lấy hoặc tạo bản ghi LearningProgress (quiz mode)
    progress = LearningProgress.query.filter_by(
        user_id=user_id, item_id=item_id, learning_mode='quiz'
    ).first()
    if not progress:
        is_first_time = True
        progress = LearningProgress(
            user_id=user_id, item_id=item_id, learning_mode='quiz'
        )
        db.session.add(progress)
        progress.first_seen = func.now()
        progress.fsrs_state = LearningProgress.STATE_LEARNING # Mặc định là learning khi mới bắt đầu

    # 2. Cập nhật các chỉ số thống kê cơ bản
    progress.last_reviewed = func.now()
    if is_correct:
        progress.times_correct = (progress.times_correct or 0) + 1
        progress.correct_streak = (progress.correct_streak or 0) + 1
        progress.incorrect_streak = 0 # Reset chuỗi sai
    else:
        progress.times_incorrect = (progress.times_incorrect or 0) + 1
        progress.incorrect_streak = (progress.incorrect_streak or 0) + 1
        progress.correct_streak = 0 # Reset chuỗi đúng

    # 3. Tính toán điểm số
    if is_first_time:
        score_change += _get_score_value('QUIZ_FIRST_TIME_BONUS', 5) # +5 điểm thưởng cho lần đầu làm câu mới

    if is_correct:
        score_change += _get_score_value('QUIZ_CORRECT_BONUS', 20) # +20 điểm cho câu trả lời đúng

    # 4. Cập nhật trạng thái (status)
    total_attempts = (progress.times_correct or 0) + (progress.times_incorrect or 0)
    correct_ratio = (progress.times_correct or 0) / total_attempts if total_attempts > 0 else 0

    if total_attempts > 10 and correct_ratio > 0.8:
        progress.fsrs_state = LearningProgress.STATE_REVIEW
    elif total_attempts > 5 and correct_ratio < 0.5:
        # [UPDATED] Do NOT set status='hard' rigidly. 
        # Use 'learning' so Memory Engine can handle spaced repetition normally.
        # "Hard" logic is now derived dynamically from streaks/mastery.
        progress.fsrs_state = LearningProgress.STATE_LEARNING
    elif is_first_time: # Nếu là lần đầu tiên, đặt là learning
        progress.fsrs_state = LearningProgress.STATE_LEARNING

    # 5. Log to ReviewLog table (replaces legacy JSON review_history)
    from mindstack_app.models import ReviewLog
    now = datetime.datetime.now(datetime.timezone.utc)
    log_entry = ReviewLog(
        user_id=user_id,
        item_id=item_id,
        timestamp=now,
        rating=1 if is_correct else 0,  # 1=correct, 0=incorrect for quiz
        review_type='quiz',
        user_answer=user_answer_text,
        is_correct=is_correct,
        score_change=score_change,
        # Session context fields
        session_id=session_id,
        container_id=container_id or item.container_id,
        mode=mode,
        streak_position=progress.correct_streak if is_correct else 0
    )
    db.session.add(log_entry)

    # 6. Cập nhật tổng điểm của người dùng
    # 6. Cập nhật điểm và ghi log thông qua ScoreService
    reason = "Quiz Correct Answer" if is_correct else "Quiz Incorrect Answer"
    if is_first_time:
        reason += " (First Time Bonus)"

    result = ScoreService.award_points(
        user_id=user_id,
        amount=score_change,
        reason=reason,
        item_id=item_id,
        item_type='QUIZ_MCQ'
    )
    
    updated_total_score = result.get('new_total') if result.get('success') and result.get('new_total') is not None else (current_user_total_score + score_change)

    # 8. Commit các thay đổi vào cơ sở dữ liệu
    db.session.commit()

    return score_change, updated_total_score, is_correct, correct_option_char, explanation

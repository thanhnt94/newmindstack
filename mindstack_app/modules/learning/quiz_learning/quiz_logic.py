# File: mindstack_app/modules/learning/quiz_learning/quiz_logic.py
# Phiên bản: 2.0
# MỤC ĐÍCH: Cập nhật logic để sử dụng model QuizProgress mới thay cho UserProgress.
# ĐÃ SỬA: Thay thế import UserProgress bằng QuizProgress.
# ĐÃ SỬA: Cập nhật logic truy vấn và tạo bản ghi để tương tác với bảng QuizProgress.
# ĐÃ SỬA: Thêm item_type vào ScoreLog khi tạo bản ghi.

from ....models import db, User, LearningItem, QuizProgress, ScoreLog
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app # Import current_app

def process_quiz_answer(user_id, item_id, user_answer_text, current_user_total_score):
    """
    Xử lý một câu trả lời Quiz của người dùng, cập nhật QuizProgress,
    tính điểm và ghi log điểm số.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của câu hỏi Quiz.
        user_answer_text (str): Đáp án mà người dùng đã chọn (ký tự lựa chọn: 'A', 'B', 'C', 'D').
        current_user_total_score (int): Tổng điểm hiện tại của người dùng trước khi xử lý câu này.

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

    # 1. Lấy hoặc tạo bản ghi QuizProgress
    progress = QuizProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    if not progress:
        is_first_time = True
        progress = QuizProgress(user_id=user_id, item_id=item_id)
        db.session.add(progress)
        progress.first_seen_timestamp = func.now()
        progress.status = 'learning' # Mặc định là learning khi mới bắt đầu

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
        score_change += 5 # +5 điểm thưởng cho lần đầu làm câu mới

    if is_correct:
        score_change += 20 # +20 điểm cho câu trả lời đúng

    # 4. Cập nhật trạng thái (status)
    total_attempts = (progress.times_correct or 0) + (progress.times_incorrect or 0)
    correct_ratio = (progress.times_correct or 0) / total_attempts if total_attempts > 0 else 0

    if total_attempts > 10 and correct_ratio > 0.8:
        progress.status = 'mastered'
    elif total_attempts > 5 and correct_ratio < 0.5:
        progress.status = 'hard'
    elif is_first_time: # Nếu là lần đầu tiên, đặt là learning
        progress.status = 'learning'

    # 5. Ghi vào review_history
    review_entry = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'user_answer': user_answer_text, # Ký tự đáp án người dùng chọn
        'is_correct': is_correct,
        'score_change': score_change,
        'total_score_after': current_user_total_score + score_change # Tính điểm tổng sau khi cập nhật
    }
    if progress.review_history is None:
        progress.review_history = []
    progress.review_history.append(review_entry)
    flag_modified(progress, "review_history") # Đánh dấu trường JSON đã thay đổi

    # 6. Cập nhật tổng điểm của người dùng
    user = User.query.get(user_id)
    if user:
        user.total_score = (user.total_score or 0) + score_change
    updated_total_score = user.total_score if user else current_user_total_score + score_change

    # 7. Ghi log vào ScoreLog
    reason = "Quiz Correct Answer" if is_correct else "Quiz Incorrect Answer"
    if is_first_time:
        reason += " (First Time Bonus)"
    
    new_score_log = ScoreLog(
        user_id=user_id,
        item_id=item_id,
        score_change=score_change,
        reason=reason,
        item_type='QUIZ_MCQ' # THÊM: Lưu loại item
    )
    db.session.add(new_score_log)

    # 8. Commit các thay đổi vào cơ sở dữ liệu
    db.session.commit()

    return score_change, updated_total_score, is_correct, correct_option_char, explanation
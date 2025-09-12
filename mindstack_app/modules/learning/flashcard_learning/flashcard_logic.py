# File: mindstack_app/modules/learning/flashcard_learning/flashcard_logic.py
# Phiên bản: 3.1 (Corrected)
# MỤC ĐÍCH: Sửa lỗi và triển khai ĐÚNG thuật toán SRS nâng cao với các giai đoạn học và đơn vị phút.
# ĐÃ SỬA: Viết lại hoàn toàn calculate_next_review và process_flashcard_answer để phản ánh đúng logic đã thống nhất.

from ....models import db, User, LearningItem, FlashcardProgress, ScoreLog
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app

# ==============================================================================
# I. CÁC HỆ SỐ CÓ THỂ TÙY CHỈNH CHO THUẬT TOÁN
# ==============================================================================

# Các bước học (tính bằng phút) cho thẻ trong giai đoạn 'learning'.
# Chuỗi này được sử dụng tuần tự cho các lần trả lời "Nhớ" liên tiếp.
LEARNING_STEPS_MINUTES = [10, 60, 240, 480, 1440, 2880]  # 10m, 1h, 4h, 8h, 1d, 2d

# Khoảng thời gian (phút) cho thẻ bị "lapsed" (quên) và cần học lại.
RELEARNING_STEP_MINUTES = 10

# Khoảng thời gian (phút) đầu tiên sau khi một thẻ "tốt nghiệp".
GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60  # 4 ngày

# ==============================================================================
# II. LOGIC TÍNH TOÁN THỜI GIAN ÔN TẬP
# ==============================================================================

def _get_next_learning_interval(repetitions):
    """
    Mô tả: Lấy khoảng thời gian học tiếp theo từ chuỗi LEARNING_STEPS_MINUTES.
    Args:
        repetitions (int): Số lần trả lời "Nhớ" liên tiếp trong giai đoạn learning.
    Returns:
        int: Khoảng thời gian tiếp theo tính bằng phút.
    """
    # repetitions bắt đầu từ 0, nên lần đúng đầu tiên (rep=1) sẽ lấy step[0]
    step_index = repetitions - 1
    if 0 <= step_index < len(LEARNING_STEPS_MINUTES):
        return LEARNING_STEPS_MINUTES[step_index]
    else:
        # Nếu đã vượt qua tất cả các bước được định nghĩa, dùng bước cuối cùng
        return LEARNING_STEPS_MINUTES[-1]

def calculate_next_review_time(progress, quality):
    """
    Mô tả: Tính toán thời gian ôn tập tiếp theo dựa trên trạng thái và chất lượng trả lời.
           Hàm này chỉ tính toán và trả về thời gian, không thay đổi trạng thái.
    Args:
        progress (FlashcardProgress): Đối tượng tiến trình của thẻ.
        quality (int): Chất lượng câu trả lời (thang điểm 0-5).
    Returns:
        datetime: Thời điểm ôn tập tiếp theo.
    """
    # ----- TRƯỜNG HỢP 1: Thẻ đang trong giai đoạn 'learning' hoặc 'relearning' -----
    if progress.status in ['learning', 'new']:
        if quality < 4:  # Nếu trả lời "Mơ hồ" hoặc "Quên"
            next_interval_minutes = RELEARNING_STEP_MINUTES
        else:  # Nếu trả lời "Nhớ"
            # repetitions được tăng lên 1 trước khi gọi hàm này
            next_interval_minutes = _get_next_learning_interval(progress.repetitions)
        
        progress.interval = next_interval_minutes

    # ----- TRƯỜNG HỢP 2: Thẻ đang trong giai đoạn 'reviewing' (ôn tập dài hạn) -----
    elif progress.status == 'reviewing':
        if quality < 3:  # Nếu trả lời "Quên"
            # Thẻ sẽ bị "Lapsed", quay lại trạng thái learning
            next_interval_minutes = RELEARNING_STEP_MINUTES
        else:  # Nếu trả lời đúng hoặc mơ hồ
            # Áp dụng công thức SM-2
            new_interval = math.ceil(progress.interval * progress.easiness_factor)
            next_interval_minutes = new_interval

        progress.interval = next_interval_minutes

    # Chuyển đổi interval (phút) thành thời điểm cụ thể
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=progress.interval)

# ==============================================================================
# III. HÀM XỬ LÝ CHÍNH
# ==============================================================================

def process_flashcard_answer(user_id, item_id, user_answer_quality, current_user_total_score):
    """
    Mô tả: Xử lý một câu trả lời Flashcard, cập nhật tiến trình, kiểm tra điều kiện tốt nghiệp,
           tính điểm và ghi log.
    """
    score_change = 0

    item = LearningItem.query.get(item_id)
    if not item:
        return 0, current_user_total_score, False, "unknown", "Lỗi: Không tìm thấy thẻ."

    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    if not progress:
        progress = FlashcardProgress(
            user_id=user_id, item_id=item_id, status='new',
            easiness_factor=2.5, repetitions=0, interval=0
        )
        db.session.add(progress)
        progress.first_seen_timestamp = func.now()

    # Nếu thẻ mới, chuyển ngay sang 'learning'
    if progress.status == 'new':
        progress.status = 'learning'

    # 1. Ghi lại lịch sử trả lời
    progress.last_reviewed = func.now()
    if progress.review_history is None:
        progress.review_history = []
    
    review_entry = {'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'user_answer_quality': user_answer_quality}
    progress.review_history.append(review_entry)
    flag_modified(progress, "review_history")

    # 2. Phân loại câu trả lời và cập nhật bộ đếm
    if user_answer_quality >= 4:
        progress.times_correct = (progress.times_correct or 0) + 1
    elif user_answer_quality >= 2:
        progress.times_vague = (progress.times_vague or 0) + 1
    else:
        progress.times_incorrect = (progress.times_incorrect or 0) + 1

    # 3. Xử lý logic trạng thái và tiến trình
    is_correct_response = user_answer_quality >= 4
    is_vague_response = 2 <= user_answer_quality <= 3
    is_incorrect_response = user_answer_quality < 2

    # Xử lý cho thẻ đang trong giai đoạn dài hạn (reviewing)
    if progress.status == 'reviewing':
        if is_incorrect_response: # Nếu quên thẻ reviewing
            progress.status = 'learning'  # Giáng cấp về learning
            progress.repetitions = 0  # Reset chuỗi học lại
            progress.easiness_factor = max(1.3, progress.easiness_factor - 0.2) # Phạt EF
        else: # Nếu nhớ hoặc mơ hồ
            progress.repetitions = (progress.repetitions or 0) + 1
            progress.easiness_factor += (0.1 - (5 - user_answer_quality) * (0.08 + (5 - user_answer_quality) * 0.02))
            if progress.easiness_factor < 1.3: progress.easiness_factor = 1.3
    
    # Xử lý cho thẻ đang trong giai đoạn học (learning)
    else: # status is 'learning'
        if is_correct_response:
            progress.repetitions = (progress.repetitions or 0) + 1
        else: # Nếu trả lời sai hoặc mơ hồ khi đang học, reset chuỗi
            progress.repetitions = 0
            
    # 4. Tính toán thời gian ôn tập tiếp theo
    progress.due_time = calculate_next_review_time(progress, user_answer_quality)

    # 5. Kiểm tra điều kiện "tốt nghiệp" sau khi đã cập nhật mọi thứ
    if progress.status == 'learning':
        total_reviews = len(progress.review_history)
        total_quality_score = sum(entry.get('user_answer_quality', 0) for entry in progress.review_history)
        average_quality = total_quality_score / total_reviews if total_reviews > 0 else 0
        
        if total_reviews >= 7 and average_quality > 3.0:
            progress.status = 'reviewing'
            progress.interval = GRADUATING_INTERVAL_MINUTES
            progress.due_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=progress.interval)
            progress.repetitions = 1 # Coi đây là lần lặp lại đầu tiên ở chế độ reviewing
            current_app.logger.info(f"Thẻ {item_id} đã TỐT NGHIỆP! Trạng thái -> reviewing.")

    # 6. Tính toán điểm số
    if user_answer_quality >= 4: score_change = 10
    elif user_answer_quality >= 2: score_change = 5
    else: score_change = 0

    # 7. Cập nhật tổng điểm và ghi log
    user = User.query.get(user_id)
    if user:
        user.total_score = (user.total_score or 0) + score_change
    updated_total_score = user.total_score if user else current_user_total_score + score_change

    new_score_log = ScoreLog(
        user_id=user_id, item_id=item_id, score_change=score_change,
        reason=f"Flashcard Answer (Quality: {user_answer_quality})", item_type='FLASHCARD'
    )
    db.session.add(new_score_log)
    db.session.commit()
    
    # 8. Lấy thống kê cuối cùng để trả về
    from .flashcard_stats_logic import get_flashcard_item_statistics
    item_stats = get_flashcard_item_statistics(user_id, item_id)

    is_considered_correct_for_status = (user_answer_quality >= 3)
    return score_change, updated_total_score, is_considered_correct_for_status, progress.status, item_stats
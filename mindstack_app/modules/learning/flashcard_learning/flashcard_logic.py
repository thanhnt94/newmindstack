# File: mindstack_app/modules/learning/flashcard_learning/flashcard_logic.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Cập nhật lại logic tính điểm theo yêu cầu mới (không trừ điểm).
# ĐÃ SỬA: Thay đổi cách tính score_change: Nhớ (+10), Mơ hồ (+5), Quên (0).
# ĐÃ SỬA: Logic is_correct giờ đây chỉ dùng để phân loại, không ảnh hưởng trực tiếp đến điểm số.

from ....models import db, User, LearningItem, FlashcardProgress, ScoreLog
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app

def calculate_next_review(progress, quality):
    """
    Tính toán thời gian ôn tập tiếp theo và cập nhật hệ số E-Factor theo thuật toán SM-2.
    - quality (chất lượng câu trả lời):
        4 = Nhớ
        2 = Mơ hồ
        1 = Quên
    """
    if quality >= 3: # Chỉ khi trả lời là "Nhớ" (quality=4)
        if progress.repetitions == 0:
            progress.interval = 1
        elif progress.repetitions == 1:
            progress.interval = 6
        else:
            progress.interval = math.ceil(progress.interval * progress.easiness_factor)
        progress.repetitions += 1
    else: # Khi trả lời là "Mơ hồ" hoặc "Quên"
        progress.repetitions = 0
        progress.interval = 1

    # Công thức SM-2 gốc sử dụng quality từ 0-5, ta cần điều chỉnh lại một chút
    # Hoặc giữ nguyên logic này vì nó vẫn hoạt động tốt để điều chỉnh độ khó
    # Ta sẽ giữ nguyên công thức này để EF vẫn được điều chỉnh linh hoạt
    sm2_quality = 0
    if quality == 4: sm2_quality = 5 # Nhớ -> Perfect
    if quality == 2: sm2_quality = 3 # Mơ hồ -> Correct but difficult
    if quality == 1: sm2_quality = 1 # Quên -> Incorrect

    progress.easiness_factor = progress.easiness_factor + (0.1 - (5 - sm2_quality) * (0.08 + (5 - sm2_quality) * 0.02))
    if progress.easiness_factor < 1.3:
        progress.easiness_factor = 1.3

    next_review_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=progress.interval)
    return next_review_time


def process_flashcard_answer(user_id, item_id, user_answer_quality, current_user_total_score):
    """
    Xử lý một câu trả lời Flashcard của người dùng, cập nhật FlashcardProgress,
    tính điểm và ghi log điểm số theo logic mới.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của thẻ Flashcard.
        user_answer_quality (int): Chất lượng câu trả lời đã được quy đổi (4: Nhớ, 2: Mơ hồ, 1: Quên).
        current_user_total_score (int): Tổng điểm hiện tại của người dùng.

    Returns:
        tuple: (score_change, updated_total_score, is_correct, new_progress_status, item_stats)
    """
    score_change = 0
    is_first_time = False

    item = LearningItem.query.get(item_id)
    if not item:
        return 0, current_user_total_score, False, None, "Lỗi: Không tìm thấy thẻ."

    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    if not progress:
        is_first_time = True
        progress = FlashcardProgress(
            user_id=user_id,
            item_id=item_id,
            easiness_factor=2.5,
            repetitions=0,
            interval=0,
            status='new'
        )
        db.session.add(progress)
        progress.first_seen_timestamp = func.now()

    progress.last_reviewed = func.now()
    # is_correct chỉ dùng để phân loại, không ảnh hưởng điểm
    is_correct = (user_answer_quality >= 3) 
    progress.due_time = calculate_next_review(progress, user_answer_quality)

    # Cập nhật streaks và times_count
    if user_answer_quality == 4: # Nhớ
        progress.times_correct = (progress.times_correct or 0) + 1
        progress.correct_streak = (progress.correct_streak or 0) + 1
        progress.incorrect_streak = 0
        progress.vague_streak = 0
    elif user_answer_quality == 2: # Mơ hồ
        progress.times_vague = (progress.times_vague or 0) + 1
        progress.vague_streak = (progress.vague_streak or 0) + 1
        progress.correct_streak = 0
        progress.incorrect_streak = 0
    else: # Quên (quality = 1)
        progress.times_incorrect = (progress.times_incorrect or 0) + 1
        progress.incorrect_streak = (progress.incorrect_streak or 0) + 1
        progress.correct_streak = 0
        progress.vague_streak = 0
        
    # SỬA ĐỔI: Áp dụng thang điểm mới
    if user_answer_quality == 4: # Nhớ
        score_change = 10
    elif user_answer_quality == 2: # Mơ hồ
        score_change = 5
    else: # Quên
        score_change = 0 # Không cộng, không trừ

    # Cập nhật trạng thái
    if progress.status == 'new' and is_correct:
        progress.status = 'learning'
    elif progress.status == 'learning' and progress.repetitions > 2 and is_correct:
        progress.status = 'mastered'
    elif user_answer_quality <= 2 and progress.easiness_factor < 1.8:
        progress.status = 'hard'
    elif progress.status == 'hard' and is_correct:
        progress.status = 'learning'
    
    review_entry = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'user_answer_quality': user_answer_quality,
        'is_correct': is_correct,
        'score_change': score_change,
        'total_score_after': current_user_total_score + score_change
    }
    if progress.review_history is None:
        progress.review_history = []
    progress.review_history.append(review_entry)
    flag_modified(progress, "review_history")

    user = User.query.get(user_id)
    if user:
        user.total_score = (user.total_score or 0) + score_change
    updated_total_score = user.total_score if user else current_user_total_score + score_change

    reason = f"Flashcard Answer (Quality: {user_answer_quality})"
    new_score_log = ScoreLog(
        user_id=user_id,
        item_id=item_id,
        score_change=score_change,
        reason=reason,
        item_type='FLASHCARD'
    )
    db.session.add(new_score_log)

    db.session.commit()
    
    from .flashcard_stats_logic import get_flashcard_item_statistics
    item_stats = get_flashcard_item_statistics(user_id, item_id)

    return score_change, updated_total_score, is_correct, progress.status, item_stats
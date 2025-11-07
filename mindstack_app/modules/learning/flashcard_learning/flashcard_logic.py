# File: mindstack_app/modules/learning/flashcard_learning/flashcard_logic.py
# Phiên bản: 3.6
# MỤC ĐÍCH: Nâng cấp logic để xử lý việc ôn tập sớm và sửa lỗi TypeError.
# ĐÃ SỬA: Khắc phục lỗi so sánh datetime bằng cách đảm bảo cả hai đối tượng đều là timezone-aware.

from ....models import db, User, LearningItem, FlashcardProgress, ScoreLog
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app
from mindstack_app.modules.shared.utils.db_session import safe_commit

# ==============================================================================
# I. CÁC HỆ SỐ CÓ THỂ TÙY CHỈNH CHO THUẬT TOÁN
# ==============================================================================

LEARNING_STEPS_MINUTES = [10, 60, 240, 480, 1440, 2880]
RELEARNING_STEP_MINUTES = 10
GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60

# ==============================================================================
# II. LOGIC TÍNH TOÁN THỜI GIAN ÔN TẬP
# ==============================================================================

def _get_next_learning_interval(repetitions):
    """
    Mô tả: Lấy khoảng thời gian học tiếp theo từ chuỗi LEARNING_STEPS_MINUTES.
    """
    step_index = repetitions - 1
    if 0 <= step_index < len(LEARNING_STEPS_MINUTES):
        return LEARNING_STEPS_MINUTES[step_index]
    else:
        return LEARNING_STEPS_MINUTES[-1]

def calculate_next_review_time(progress, quality):
    """
    Mô tả: Tính toán thời gian ôn tập tiếp theo dựa trên trạng thái và chất lượng trả lời.
    """
    if progress.status in ['learning', 'new']:
        if quality < 3:
            next_interval_minutes = RELEARNING_STEP_MINUTES
        else:
            next_interval_minutes = _get_next_learning_interval(progress.repetitions)
        progress.interval = next_interval_minutes
    elif progress.status == 'reviewing':
        if quality < 3:
            next_interval_minutes = RELEARNING_STEP_MINUTES
        else:
            new_interval = math.ceil(progress.interval * progress.easiness_factor)
            next_interval_minutes = new_interval
        progress.interval = next_interval_minutes

    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=progress.interval)

# ==============================================================================
# III. HÀM XỬ LÝ CHÍNH
# ==============================================================================

def process_flashcard_answer(user_id, item_id, user_answer_quality, current_user_total_score, mode=None):
    """
    Mô tả: Xử lý một câu trả lời Flashcard, cập nhật tiến trình, tính điểm và ghi log.
    """
    score_change = 0

    item = LearningItem.query.get(item_id)
    if not item:
        return 0, current_user_total_score, 'error', "Lỗi: Không tìm thấy thẻ.", None

    is_all_review_mode = mode == 'all_review'

    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    now = datetime.datetime.now(datetime.timezone.utc)
    if not progress:
        progress = FlashcardProgress(
            user_id=user_id, item_id=item_id, status='new',
            easiness_factor=2.5, repetitions=0, interval=0
        )
        db.session.add(progress)
        progress.first_seen_timestamp = now
    elif progress.first_seen_timestamp is None:
        progress.first_seen_timestamp = now
    elif progress.first_seen_timestamp.tzinfo is None:
        progress.first_seen_timestamp = progress.first_seen_timestamp.replace(tzinfo=datetime.timezone.utc)

    if user_answer_quality is None:
        if progress.review_history is None:
            progress.review_history = []

        is_first_preview = len(progress.review_history) == 0
        was_new_card = progress.status == 'new'

        preview_entry = {
            'timestamp': now.isoformat(),
            'user_answer_quality': None,
            'type': 'preview'
        }
        progress.review_history.append(preview_entry)
        flag_modified(progress, "review_history")

        if was_new_card:
            progress.status = 'learning'
            progress.repetitions = 1
            preview_interval_minutes = _get_next_learning_interval(progress.repetitions)
        else:
            progress.repetitions = progress.repetitions or 1
            preview_interval_minutes = progress.interval or _get_next_learning_interval(progress.repetitions)

        progress.interval = preview_interval_minutes
        progress.due_time = now + datetime.timedelta(minutes=preview_interval_minutes)
        progress.last_reviewed = now

        user = User.query.get(user_id)
        score_change = 0
        if is_first_preview and was_new_card:
            score_change = 10
            if user:
                user.total_score = (user.total_score or 0) + score_change
            new_score_log = ScoreLog(
                user_id=user_id,
                item_id=item_id,
                score_change=score_change,
                reason="Flashcard New Card Preview Bonus",
                item_type='FLASHCARD'
            )
            db.session.add(new_score_log)

        safe_commit(db.session)

        if user:
            updated_total_score = user.total_score
        else:
            updated_total_score = current_user_total_score + score_change

        from .flashcard_stats_logic import get_flashcard_item_statistics
        item_stats = get_flashcard_item_statistics(user_id, item_id)

        return score_change, updated_total_score, 'preview', progress.status, item_stats

    # Khắc phục lỗi so sánh timezone-aware và timezone-naive
    now = datetime.datetime.now(datetime.timezone.utc)
    # Gán múi giờ cho due_time nếu nó tồn tại và chưa có múi giờ
    due_time_aware = progress.due_time
    if due_time_aware and due_time_aware.tzinfo is None:
        due_time_aware = due_time_aware.replace(tzinfo=datetime.timezone.utc)

    # Kiểm tra nếu thẻ được ôn tập trước thời hạn
    if due_time_aware and now < due_time_aware:
        current_app.logger.info(f"Thẻ {item_id} được ôn tập sớm. Chỉ cập nhật điểm và lịch sử.")
        
        if user_answer_quality >= 4:
            score_change = 10
        elif user_answer_quality >= 2:
            score_change = 5
        else:
            score_change = 0

        review_entry = {'timestamp': now.isoformat(), 'user_answer_quality': user_answer_quality}
        if progress.review_history is None:
            progress.review_history = []
        progress.review_history.append(review_entry)
        flag_modified(progress, "review_history")
        progress.last_reviewed = now

        user = User.query.get(user_id)
        if user:
            user.total_score = (user.total_score or 0) + score_change
        updated_total_score = user.total_score if user else current_user_total_score + score_change

        new_score_log = ScoreLog(
            user_id=user_id, item_id=item_id, score_change=score_change,
            reason=f"Flashcard Early Review (Quality: {user_answer_quality})", item_type='FLASHCARD'
        )
        db.session.add(new_score_log)
        safe_commit(db.session)

        if user_answer_quality >= 4:
            answer_result_type = 'correct'
        elif user_answer_quality >= 2:
            answer_result_type = 'vague'
        else:
            answer_result_type = 'incorrect'

        from .flashcard_stats_logic import get_flashcard_item_statistics
        item_stats = get_flashcard_item_statistics(user_id, item_id)

        return score_change, updated_total_score, answer_result_type, progress.status, item_stats


    # Logic cũ (khi thẻ đến hạn hoặc là thẻ mới)
    if progress.status == 'new':
        progress.status = 'learning'

    progress.last_reviewed = now
    if progress.review_history is None:
        progress.review_history = []
    
    review_entry = {'timestamp': now.isoformat(), 'user_answer_quality': user_answer_quality}
    progress.review_history.append(review_entry)
    flag_modified(progress, "review_history")

    answer_result_type = ''
    if user_answer_quality >= 4:
        progress.times_correct = (progress.times_correct or 0) + 1
        answer_result_type = 'correct'
    elif user_answer_quality >= 2:
        progress.times_vague = (progress.times_vague or 0) + 1
        answer_result_type = 'vague'
    else:
        progress.times_incorrect = (progress.times_incorrect or 0) + 1
        answer_result_type = 'incorrect'

    is_correct_response = user_answer_quality >= 4
    is_incorrect_response = user_answer_quality < 2

    if not is_all_review_mode:
        if progress.status == 'reviewing':
            if is_incorrect_response:
                progress.status = 'learning'
                progress.repetitions = 0
                progress.easiness_factor = max(1.3, progress.easiness_factor - 0.2)
            else:
                progress.repetitions = (progress.repetitions or 0) + 1
                progress.easiness_factor += (0.1 - (5 - user_answer_quality) * (0.08 + (5 - user_answer_quality) * 0.02))
                if progress.easiness_factor < 1.3: progress.easiness_factor = 1.3
        else:
            if is_correct_response:
                progress.repetitions = (progress.repetitions or 0) + 1
            elif is_incorrect_response:
                progress.repetitions = 0

        progress.due_time = calculate_next_review_time(progress, user_answer_quality)

    if progress.status == 'learning':
        review_history = progress.review_history or []
        filtered_history = [entry for entry in review_history if isinstance(entry, dict)]
        total_reviews = len(filtered_history)
        total_quality_score = sum((entry.get('user_answer_quality') or 0) for entry in filtered_history)
        average_quality = total_quality_score / total_reviews if total_reviews > 0 else 0
        
        if total_reviews >= 7 and average_quality > 3.0:
            progress.status = 'reviewing'
            progress.interval = GRADUATING_INTERVAL_MINUTES
            progress.due_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=progress.interval)
            progress.repetitions = 1
            current_app.logger.info(f"Thẻ {item_id} đã TỐT NGHIỆP! Trạng thái -> reviewing.")

    if user_answer_quality >= 4: score_change = 10
    elif user_answer_quality >= 2: score_change = 5
    else: score_change = 0

    user = User.query.get(user_id)
    if user:
        user.total_score = (user.total_score or 0) + score_change
    updated_total_score = user.total_score if user else current_user_total_score + score_change

    new_score_log = ScoreLog(
        user_id=user_id, item_id=item_id, score_change=score_change,
        reason=f"Flashcard Answer (Quality: {user_answer_quality})", item_type='FLASHCARD'
    )
    db.session.add(new_score_log)
    safe_commit(db.session)
    
    from .flashcard_stats_logic import get_flashcard_item_statistics
    item_stats = get_flashcard_item_statistics(user_id, item_id)

    return score_change, updated_total_score, answer_result_type, progress.status, item_stats

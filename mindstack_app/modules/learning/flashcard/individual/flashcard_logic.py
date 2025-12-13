# File: mindstack_app/modules/learning/flashcard_learning/flashcard_logic.py
# Phiên bản: 3.7
# MỤC ĐÍCH: Nâng cấp logic để hỗ trợ chế độ Collab không ảnh hưởng SRS.
# ĐÃ SỬA: Thêm tham số update_srs để kiểm soát việc cập nhật tiến độ học tập.

from .....models import db, User, LearningItem, FlashcardProgress
from mindstack_app.modules.gamification.services import ScoreService
from sqlalchemy.orm.attributes import flag_modified
import datetime
import math
from flask import current_app
from mindstack_app.modules.shared.utils.db_session import safe_commit
from mindstack_app.services.config_service import get_runtime_config

# ... (Các hằng số và hàm _get_score_value giữ nguyên) ...
# ==============================================================================
# I. CÁC HỆ SỐ CÓ THỂ TÙY CHỈNH CHO THUẬT TOÁN
# ==============================================================================

LEARNING_STEPS_MINUTES = [10, 60, 240, 480, 1440, 2880]
RELEARNING_STEP_MINUTES = 10
GRADUATING_INTERVAL_MINUTES = 4 * 24 * 60


def _get_score_value(key: str, default: int) -> int:
    """Fetch an integer score value from runtime config with fallback."""

    raw_value = get_runtime_config(key, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default

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

def process_flashcard_answer(user_id, item_id, user_answer_quality, current_user_total_score, mode=None, update_srs=True):
    """
    Mô tả: Xử lý một câu trả lời Flashcard, cập nhật tiến trình, tính điểm và ghi log.
    Tham số update_srs: Nếu False, chỉ tính điểm, không cập nhật tiến độ SRS (dùng cho Collab).
    """
    score_change = 0

    item = LearningItem.query.get(item_id)
    if not item:
        return 0, current_user_total_score, 'error', "Lỗi: Không tìm thấy thẻ.", None

    is_all_review_mode = mode == 'all_review'

    # Lấy hoặc tạo mới progress object, nhưng chỉ lưu nếu update_srs=True hoặc chưa có record
    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if not progress:
        # Luôn tạo record mới nếu chưa có để tránh lỗi truy cập thuộc tính sau này
        # Nhưng nếu update_srs=False thì record này sẽ ở trạng thái 'new' mãi mãi
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

    # Xử lý xem trước (preview)
    if user_answer_quality is None:
        if update_srs:
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
                score_change = _get_score_value('FLASHCARD_PREVIEW_BONUS', 10)
                ScoreService.award_points(
                    user_id=user_id,
                    amount=score_change,
                    reason="Flashcard New Card Preview Bonus",
                    item_id=item_id,
                    item_type='FLASHCARD'
                )

            safe_commit(db.session)

            if user:
                # Reload user để lấy điểm mới nhất từ DB
                db.session.refresh(user)
                updated_total_score = user.total_score
            else:
                updated_total_score = current_user_total_score + score_change
        else:
            # Nếu không update SRS, chỉ trả về thông tin hiện tại
            updated_total_score = current_user_total_score

        from .flashcard_stats_logic import get_flashcard_item_statistics
        item_stats = get_flashcard_item_statistics(user_id, item_id)

        return score_change, updated_total_score, 'preview', progress.status, item_stats

    # === XỬ LÝ TRẢ LỜI THẺ ===
    
    answer_result_type = ''
    if user_answer_quality >= 4:
        if update_srs: progress.times_correct = (progress.times_correct or 0) + 1
        answer_result_type = 'correct'
    elif user_answer_quality >= 2:
        if update_srs: progress.times_vague = (progress.times_vague or 0) + 1
        answer_result_type = 'vague'
    else:
        if update_srs: progress.times_incorrect = (progress.times_incorrect or 0) + 1
        answer_result_type = 'incorrect'

    # CHỈ CẬP NHẬT SRS NẾU ĐƯỢC PHÉP
    if update_srs:
        now = datetime.datetime.now(datetime.timezone.utc)
        due_time_aware = progress.due_time
        if due_time_aware and due_time_aware.tzinfo is None:
            due_time_aware = due_time_aware.replace(tzinfo=datetime.timezone.utc)

        # Kiểm tra ôn tập sớm
        is_early_review = due_time_aware and now < due_time_aware
        
        if is_early_review:
            current_app.logger.info(f"Thẻ {item_id} được ôn tập sớm. Chỉ cập nhật điểm và lịch sử.")
            # Logic ôn sớm: chỉ ghi log, không đổi lịch
            review_entry = {'timestamp': now.isoformat(), 'user_answer_quality': user_answer_quality}
            if progress.review_history is None:
                progress.review_history = []
            progress.review_history.append(review_entry)
            flag_modified(progress, "review_history")
            progress.last_reviewed = now
            
            # Tính điểm cho ôn sớm
            if user_answer_quality >= 4:
                score_change = _get_score_value('FLASHCARD_EARLY_REVIEW_HIGH', 10)
            elif user_answer_quality >= 2:
                score_change = _get_score_value('FLASHCARD_EARLY_REVIEW_MEDIUM', 5)
            else:
                score_change = 0
                
        else:
            # Logic ôn đúng hạn: cập nhật SRS đầy đủ
            if progress.status == 'new':
                progress.status = 'learning'

            progress.last_reviewed = now
            if progress.review_history is None:
                progress.review_history = []
            
            review_entry = {'timestamp': now.isoformat(), 'user_answer_quality': user_answer_quality}
            progress.review_history.append(review_entry)
            flag_modified(progress, "review_history")

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

            # Tính điểm chuẩn
            if user_answer_quality >= 4:
                score_change = _get_score_value('FLASHCARD_REVIEW_HIGH', 10)
            elif user_answer_quality >= 2:
                score_change = _get_score_value('FLASHCARD_REVIEW_MEDIUM', 5)
            else:
                score_change = 0
    else:
        # Trường hợp update_srs=False (Collab Mode)
        # Vẫn tính điểm nhưng theo logic đơn giản hơn hoặc giống ôn tập sớm
        if user_answer_quality >= 4:
            score_change = _get_score_value('FLASHCARD_COLLAB_CORRECT', 10) # Có thể dùng config riêng
        elif user_answer_quality >= 2:
            score_change = _get_score_value('FLASHCARD_COLLAB_VAGUE', 5)
        else:
            score_change = 0

    # Cập nhật điểm cho User
    # Cập nhật điểm cho User thông qua ScoreService
    log_reason = f"Flashcard Answer (Quality: {user_answer_quality})"
    if not update_srs:
        log_reason += " [Collab Mode]"

    result = ScoreService.award_points(
        user_id=user_id,
        amount=score_change,
        reason=log_reason,
        item_id=item_id,
        item_type='FLASHCARD'
    )
    
    updated_total_score = result.get('new_total') if result.get('success') and result.get('new_total') is not None else (current_user_total_score + score_change)
    
    safe_commit(db.session)
    
    from .flashcard_stats_logic import get_flashcard_item_statistics
    item_stats = get_flashcard_item_statistics(user_id, item_id)

    return score_change, updated_total_score, answer_result_type, progress.status, item_stats

# File: mindstack_app/modules/learning/flashcard/collab/flashcard_collab_logic.py
# MỤC ĐÍCH: Xử lý logic trả lời flashcard riêng cho chế độ Collab (Học nhóm).
# TÍNH NĂNG:
# 1. Tính điểm dựa trên chất lượng câu trả lời.
# 2. Cập nhật điểm tổng của User.
# 3. Ghi log điểm (ScoreLog).
# 4. Cập nhật tiến độ SRS của PHÒNG HỌC (FlashcardRoomProgress).

from datetime import datetime, timezone, timedelta
import math
from flask import current_app
from mindstack_app.core.extensions import db
from mindstack_app.models import User, LearningItem, ScoreLog, FlashcardRoomProgress, FlashcardCollabRound, FlashcardCollabAnswer
from mindstack_app.utils.db_session import safe_commit
# --- CẤU HÌNH SRS ---
LEARNING_STEPS_MINUTES = [1, 10]  # Steps cho thẻ đang học: 1p, 10p
GRADUATING_INTERVAL_MINUTES = 1440 # 1 ngày
EASY_INTERVAL_MINUTES = 4320 # 3 ngày
INITIAL_EASINESS_FACTOR = 2.5

def _get_score_config(key, default):
    try:
        from mindstack_app.services.config_service import get_runtime_config
        return int(get_runtime_config(key, default))
    except:
        return default

def process_collab_flashcard_answer(user_id, item_id, user_answer_quality):
    """
    Xử lý câu trả lời CÁ NHÂN trong phòng Collab.
    Chỉ tính điểm thi đua, KHÔNG cập nhật SRS cá nhân, KHÔNG cập nhật SRS phòng (việc đó làm khi hết round).
    """
    item = LearningItem.query.get(item_id)
    if not item:
        return 0, 0, 'error', "Lỗi: Không tìm thấy thẻ.", {}

    # 1. Xác định điểm số
    score_change = 0
    answer_result_type = 'incorrect'

    if user_answer_quality >= 4:
        score_change = _get_score_config('FLASHCARD_COLLAB_CORRECT', 10)
        answer_result_type = 'correct'
    elif user_answer_quality >= 2:
        score_change = _get_score_config('FLASHCARD_COLLAB_VAGUE', 5)
        answer_result_type = 'vague'
    else:
        score_change = 0
        answer_result_type = 'incorrect'

    # 2. Cập nhật User Score
    user = User.query.get(user_id)
    current_total_score = 0
    if user:
        user.total_score = (user.total_score or 0) + score_change
        current_total_score = user.total_score
        
        # 3. Ghi log
        new_score_log = ScoreLog(
            user_id=user_id,
            item_id=item_id,
            score_change=score_change,
            reason=f"Collab Answer (Quality: {user_answer_quality})",
            item_type='FLASHCARD'
        )
        db.session.add(new_score_log)
        safe_commit(db.session)

    # 4. Trả về kết quả
    item_stats = {
        'status': 'collab',
        'next_review': None,
        'interval': 0
    }

    return score_change, current_total_score, answer_result_type, 'collab_view', item_stats


def calculate_room_srs(room_id, round_id):
    """
    Tính toán và cập nhật FSRS cho PHÒNG HỌC sau khi kết thúc một vòng.
    Dựa trên điểm trung bình của tất cả người chơi.
    """
    from mindstack_app.modules.fsrs.interface import FSRSInterface
    from mindstack_app.modules.fsrs.schemas import CardStateDTO, CardStateEnum
    
    current_app.logger.info(f"Bắt đầu tính toán FSRS cho Room {room_id}, Round {round_id}")
    
    round_obj = FlashcardCollabRound.query.get(round_id)
    if not round_obj:
        return

    answers = FlashcardCollabAnswer.query.filter_by(round_id=round_id).all()
    if not answers:
        return

    # 1. Tính điểm chất lượng trung bình (0-5) -> Map to FSRS 1-4
    total_quality = sum((a.answer_quality or 0) for a in answers)
    avg_quality = total_quality / len(answers)
    
    # Simple mapping for group average
    if avg_quality >= 4.5: fsrs_rating = 4 # Easy
    elif avg_quality >= 3.0: fsrs_rating = 3 # Good
    elif avg_quality >= 2.0: fsrs_rating = 2 # Hard
    else: fsrs_rating = 1 # Again

    # 2. Lấy hoặc tạo Progress của Phòng
    progress = FlashcardRoomProgress.query.filter_by(room_id=room_id, item_id=round_obj.item_id).first()
    now = datetime.now(timezone.utc)
    
    if not progress:
        progress = FlashcardRoomProgress(
            room_id=room_id,
            item_id=round_obj.item_id,
            fsrs_state=CardStateEnum.NEW,
            fsrs_stability=0.0,
            fsrs_difficulty=0.0,
            repetitions=0,
            current_interval=0.0,
            last_reviewed=now
        )
        db.session.add(progress)
        db.session.flush()
    
    # 3. Apply FSRS logic
    # Use system-wide global weights for rooms (since it's a shared environment)
    from mindstack_app.modules.fsrs.logics.fsrs_engine import FSRSEngine
    
    # Get config via interface
    desired_retention = float(FSRSInterface.get_config('FSRS_DESIRED_RETENTION', 0.9))
    global_weights = FSRSInterface.get_config('FSRS_GLOBAL_WEIGHTS')
    
    engine = FSRSEngine(custom_weights=global_weights, desired_retention=desired_retention)
    
    card_dto = CardStateDTO(
        stability=progress.fsrs_stability or 0.0,
        difficulty=progress.fsrs_difficulty or 0.0,
        reps=progress.repetitions or 0,
        lapses=progress.lapses or 0,
        state=progress.fsrs_state,
        last_review=progress.last_reviewed.replace(tzinfo=timezone.utc) if progress.last_reviewed else None,
        scheduled_days=progress.current_interval or 0.0
    )
    
    new_card, next_due, _ = engine.review_card(card_dto, fsrs_rating, now=now)
    
    # 4. Update Progress
    progress.fsrs_state = new_card.state
    progress.fsrs_stability = new_card.stability
    progress.fsrs_difficulty = new_card.difficulty
    progress.current_interval = new_card.scheduled_days
    progress.repetitions = new_card.reps
    progress.lapses = new_card.lapses
    progress.fsrs_due = next_due
    progress.last_reviewed = now
    
    try:
        safe_commit(db.session)
        current_app.logger.info(f"Đã cập nhật FSRS Room: Item {round_obj.item_id} due in {new_card.scheduled_days:.2f} days")
    except Exception as e:
        current_app.logger.error(f"Lỗi cập nhật FSRS Room: {e}")
        db.session.rollback()

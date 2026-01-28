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
from mindstack_app.db_instance import db
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
    Tính toán và cập nhật SRS cho PHÒNG HỌC sau khi kết thúc một vòng.
    Dựa trên điểm trung bình của tất cả người chơi.
    """
    current_app.logger.info(f"Bắt đầu tính toán SRS cho Room {room_id}, Round {round_id}")
    
    round_obj = FlashcardCollabRound.query.get(round_id)
    if not round_obj:
        return

    answers = FlashcardCollabAnswer.query.filter_by(round_id=round_id).all()
    if not answers:
        return

    # 1. Tính điểm chất lượng trung bình (0-5)
    total_quality = sum((a.answer_quality or 0) for a in answers)
    avg_quality = total_quality / len(answers)
    
    # Làm tròn về thang 0-5 gần nhất để dễ xử lý SRS
    # Tuy nhiên, ta có thể dùng số thực để tính toán chính xác hơn
    current_app.logger.info(f"Room {room_id} - Item {round_obj.item_id}: Average Quality = {avg_quality}")

    # 2. Lấy hoặc tạo Progress của Phòng
    progress = FlashcardRoomProgress.query.filter_by(room_id=room_id, item_id=round_obj.item_id).first()
    now = datetime.now(timezone.utc)
    
    if not progress:
        progress = FlashcardRoomProgress(
            room_id=room_id,
            item_id=round_obj.item_id,
            status='new',
            easiness_factor=INITIAL_EASINESS_FACTOR,
            repetitions=0,
            interval=0,
            last_reviewed=now
        )
        db.session.add(progress)
    
    progress.last_reviewed = now

    # 3. Áp dụng thuật toán SRS (SM-2 simplified for Groups)
    # Quy tắc:
    # - Avg < 3: Fail (Quên) -> Reset về đầu
    # - Avg >= 3: Pass (Nhớ) -> Tăng interval
    
    if avg_quality < 3:
        # Nhóm trả lời sai nhiều -> Reset
        progress.repetitions = 0
        progress.interval = 1 # 1 phút sau hỏi lại
        progress.status = 'learning'
        # Giảm EF nhẹ
        progress.easiness_factor = max(1.3, progress.easiness_factor - 0.2)
        
    else:
        # Nhóm trả lời đúng
        if progress.status == 'new':
            progress.status = 'learning'
            progress.repetitions = 0
        
        # Tính interval mới
        if progress.repetitions == 0:
            progress.interval = 1 # Step 1
        elif progress.repetitions == 1:
            progress.interval = 10 # Step 2
        else:
            if progress.interval == 0:
                progress.interval = 1
            # Công thức: I(n) = I(n-1) * EF
            progress.interval = math.ceil(progress.interval * progress.easiness_factor)
        
        progress.repetitions += 1
        
        # Cập nhật EF
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        q = avg_quality
        progress.easiness_factor = progress.easiness_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if progress.easiness_factor < 1.3:
            progress.easiness_factor = 1.3
            
        # Nếu đã học đủ lâu -> Reviewing
        if progress.repetitions > 2:
            progress.status = 'reviewing'

    # 4. Cập nhật Due Time
    progress.due_time = now + timedelta(minutes=progress.interval)
    
    try:
        safe_commit(db.session)
        current_app.logger.info(f"Đã cập nhật SRS Room: Due in {progress.interval} mins")
    except Exception as e:
        current_app.logger.error(f"Lỗi cập nhật SRS Room: {e}")
        db.session.rollback()
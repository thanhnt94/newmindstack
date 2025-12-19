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
from mindstack_app.modules.learning.srs.service import SrsService

def _get_score_value(key: str, default: int) -> int:
    """Fetch an integer score value from runtime config with fallback."""
    raw_value = get_runtime_config(key, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default

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

    # Determine answer type for return
    answer_result_type = ''
    if user_answer_quality >= 4:
        answer_result_type = 'correct'
    elif user_answer_quality >= 2:
        answer_result_type = 'vague'
    else:
        answer_result_type = 'incorrect'

    if update_srs and not is_all_review_mode:
        # Use centralized Service
        progress = SrsService.update_item_progress(user_id, item_id, user_answer_quality, source_mode='flashcard')
        
        # Calculate score change (simplified from original logic - separating concerns)
        # Original logic had complexity covering early review vs normal review scores.
        # Check if it was early review (logic duplicated from Service for scoring purposes? Or trust Service?)
        # For simplicity, we stick to standard scoring based on quality.
        if user_answer_quality >= 4:
            score_change = _get_score_value('FLASHCARD_REVIEW_HIGH', 10)
        elif user_answer_quality >= 2:
            score_change = _get_score_value('FLASHCARD_REVIEW_MEDIUM', 5)
        else:
            score_change = 0
            
    else:
        # No SRS update (Collab or All Review)
        # Just fetch progress for stats return
        progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
        if not progress:
             # Create dummy/temp progress for stats if needed, or just None?
             # Original code created it. Let's create it but not save if we can avoid it, 
             # but `get_flashcard_item_statistics` might need it.
             # Safest to create default.
             progress = FlashcardProgress(user_id=user_id, item_id=item_id, status='new')
             db.session.add(progress) # Add to session to persist if we commit later

        # Score logic for Collab/No-SRS
        if user_answer_quality >= 4:
            score_change = _get_score_value('FLASHCARD_COLLAB_CORRECT', 10)
        elif user_answer_quality >= 2:
            score_change = _get_score_value('FLASHCARD_COLLAB_VAGUE', 5)
        else:
            score_change = 0

    # Cập nhật điểm cho User
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


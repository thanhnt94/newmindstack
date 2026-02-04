# File: mindstack_app/modules/learning/quiz_learning/quiz_logic.py
# Phiên bản: 3.2
# MỤC ĐÍCH: Refactor to use ItemMemoryState (FSRS) instead of LearningProgress.

from mindstack_app.models import LearningItem, User, db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.gamification.services.scoring_service import ScoreService
from mindstack_app.modules.learning_history.services import HistoryRecorder
from sqlalchemy.sql import func
import datetime
from flask import current_app

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
    Xử lý một câu trả lời Quiz của người dùng, cập nhật ItemMemoryState,
    tính điểm và ghi log điểm số.
    """
    score_change = 0
    is_first_time = False

    # Lấy thông tin câu hỏi
    item = LearningItem.query.get(item_id)
    if not item:
        return 0, current_user_total_score, False, None, "Lỗi: Không tìm thấy câu hỏi."

    # [REFACTORED] Use ContentInterface
    from mindstack_app.modules.content_management.interface import ContentInterface
    content_map = ContentInterface.get_items_content([item_id])
    std_content = content_map.get(item_id) or {}

    # Lấy đáp án đúng (dạng văn bản) và các lựa chọn
    correct_answer_text_from_db = std_content.get('correct_answer')
    options = std_content.get('options', {})
    explanation = std_content.get('explanation') # Interface handles fallback to ai_explanation

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

    # 1. Lấy hoặc tạo bản ghi ItemMemoryState
    # Note: unified state, ignoring 'quiz' mode in query
    state_record = ItemMemoryState.query.filter_by(
        user_id=user_id, item_id=item_id
    ).first()
    
    if not state_record:
        is_first_time = True
        state_record = ItemMemoryState(
            user_id=user_id, item_id=item_id,
            state=0, # NEW
            data={}
        )
        db.session.add(state_record)
        state_record.created_at = func.now()

    # 2. Cập nhật các chỉ số thống kê cơ bản
    state_record.last_review = func.now()
    
    # Update unified counters
    if is_correct:
        state_record.times_correct = (state_record.times_correct or 0) + 1
        state_record.streak = (state_record.streak or 0) + 1
    else:
        state_record.times_incorrect = (state_record.times_incorrect or 0) + 1
        state_record.streak = 0
    
    # 3. Tính toán điểm số
    if is_first_time:
        score_change += _get_score_value('QUIZ_FIRST_TIME_BONUS', 5)

    if is_correct:
        score_change += _get_score_value('QUIZ_CORRECT_BONUS', 20)

    # 4. Cập nhật trạng thái (status)
    # Legacy heuristic logic ported to new model
    total_attempts = (state_record.times_correct or 0) + (state_record.times_incorrect or 0)
    correct_ratio = (state_record.times_correct or 0) / total_attempts if total_attempts > 0 else 0

    if total_attempts > 10 and correct_ratio > 0.8:
        state_record.state = 2 # REVIEW
    elif total_attempts > 5 and correct_ratio < 0.5:
        state_record.state = 1 # LEARNING
    elif is_first_time:
        state_record.state = 1 # LEARNING

    # 5. Log to HistoryRecorder
    HistoryRecorder.record_interaction(
        user_id=user_id,
        item_id=item_id,
        result_data={
            'rating': 1 if is_correct else 0, # 1=correct, 0=incorrect for quiz
            'user_answer': user_answer_text,
            'is_correct': is_correct,
            'review_duration': 0
        },
        context_data={
            'session_id': session_id,
            'container_id': container_id or item.container_id,
            'learning_mode': 'quiz'
        },
        fsrs_snapshot={
            'state': state_record.state,
            'stability': state_record.stability,
            'difficulty': state_record.difficulty
        },
        game_snapshot={
            'score_change': score_change,
            'streak_position': state_record.streak if is_correct else 0
        }
    )

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

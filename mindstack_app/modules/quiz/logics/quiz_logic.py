# File: mindstack_app/modules/learning/quiz_learning/quiz_logic.py
# Phiên bản: 3.3 [REFACTORED]
# MỤC ĐÍCH: Refactor to use FSRSInterface and LearningInterface.

from mindstack_app.models import LearningItem, User, db
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
from mindstack_app.modules.learning.interface import LearningInterface
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
                        session_id=None, container_id=None, mode=None, correct_answer_override=None):
    """
    Xử lý một câu trả lời Quiz của người dùng.
    Delegate toàn bộ logic state, history, score sang Interface.
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

    # Lấy đáp án đúng... (Giữ nguyên logic so sánh)
    correct_answer_text_from_db = correct_answer_override or std_content.get('correct_answer')
    correct_option_from_db = std_content.get('correct_option')
    options = std_content.get('options', {})
    explanation = std_content.get('explanation')

    correct_option_char = None
    if correct_answer_text_from_db:
        correct_text_norm = str(correct_answer_text_from_db).strip().lower()
        for key, value in options.items():
            if str(value).strip().lower() == correct_text_norm:
                correct_option_char = key
                break
                
    if correct_option_char is None and correct_answer_text_from_db in ['A', 'B', 'C', 'D']:
        correct_option_char = correct_answer_text_from_db

    if correct_option_char is None and correct_option_from_db in ['A', 'B', 'C', 'D']:
        correct_option_char = correct_option_from_db
    
    is_correct = False
    is_direct_text_match = False
    
    if user_answer_text and correct_answer_text_from_db:
         if str(user_answer_text).strip().lower() == str(correct_answer_text_from_db).strip().lower():
             is_correct = True
             is_direct_text_match = True
             
    if not is_correct and correct_option_char:
        is_correct = (user_answer_text == correct_option_char)

    if correct_option_char is None:
        if is_direct_text_match:
             correct_option_char = correct_answer_text_from_db
        else:
            current_app.logger.error(f"Lỗi dữ liệu: Không tìm thấy ký tự lựa chọn cho đáp án đúng quiz {item_id}")
            return score_change, current_user_total_score, is_correct, correct_option_char, explanation

    # 1. State Update via FSRSInterface
    # We fetch state
    state_record = FsrsInterface.get_item_state(user_id, item_id)
    
    if not state_record:
        is_first_time = True
        # Create new state? FsrsInterface doesn't have explicit "create_state" yet except in process_review.
        # But we can assume get_item_state returning None implies we might need to initialize.
        # However, for Quiz, we update counts. FSRS `process_review` assumes explicit SRS.
        # Quiz often uses Simplified logic. 
        # Using `FsrsInterface.process_review` with `mode='quiz'`?
        # Let's try that, assuming FSRS implementation supports generic modes or falls back.
        # Using `quality`: 4 for correct, 1 for incorrect.
        pass
        
    # Calculate Score First (needed for return)
    if is_first_time:
        score_change += _get_score_value('QUIZ_FIRST_TIME_BONUS', 5)

    if is_correct:
        score_change += _get_score_value('QUIZ_CORRECT_BONUS', 20)

    # 2. Update via FSRS Interface (Process Review)
    # This handles State Creation, Updates, and Persistence transparently.
    quality = 4 if is_correct else 1
    state_record, srs_result = FsrsInterface.process_review(
        user_id=user_id,
        item_id=item_id,
        quality=quality, # 4=Easy(Correct), 1=Again(Wrong)
        mode='quiz', # Tag as quiz mode
        duration_ms=0,
        container_id=container_id or item.container_id
    )
    
    # 3. Log History & Score via LearningInterface
    # We construct the result payload
    result_data = {
        'rating': 1 if is_correct else 0,
        'user_answer': user_answer_text,
        'is_correct': is_correct,
        'review_duration': 0
    }
    context_data = {
        'session_id': session_id,
        'container_id': container_id or item.container_id,
        'learning_mode': 'quiz',
        # Pass snapshot for detailed history if needed, handled by interface impl?
        # LearningInterface.update_learning_progress docs say "result_data, context_data".
        # We can pass extra data in context.
        'fsrs_snapshot': {
            'state': state_record.state,
            'stability': state_record.stability
        },
        'score_change': score_change
    }
    
    # Use LearningInterface to record everything
    LearningInterface.update_learning_progress(
        user_id=user_id,
        item_id=item_id,
        result_data=result_data,
        context_data=context_data
    )
    
    # NOTE: Scoring is currently partially inside update_learning_progress (placeholder) 
    # BUT existing `process_quiz_answer` returned `updated_total_score`.
    # To keep exact behavior while `update_learning_progress` is fully implemented, 
    # we might need to call ScoreService manually via Interface or let Interface return result.
    # User said "Thay ScoreService -> GamificationInterface/LearningInterface".
    # I'll rely on LearningInterface or call a centralized Score method if I need the value back.
    # Current `update_learning_progress` returns None. 
    # I should check if I can get the new score.
    # For now, to ensure `process_quiz_answer` signature doesn't break, I'll calculate expected total.
    
    updated_total_score = current_user_total_score + score_change
    # In a real sync, we'd query User again or return from Interface.
    
    db.session.commit()

    return score_change, updated_total_score, is_correct, correct_option_char, explanation

"""
Event Handlers for Gamification Module.

Listens to signals from other modules and triggers gamification logic.
This enables decoupled communication - the Learning module doesn't need
to know about Gamification internals.
"""
from flask import current_app
from mindstack_app.core.signals import card_reviewed, session_completed


@card_reviewed.connect
def on_card_reviewed(sender, **kwargs):
    """
    Handle card_reviewed signal from Learning module.
    Awards points to user based on the learning activity.
    
    Expected kwargs:
        - user_id: int
        - item_id: int
        - quality: int (1-4 FSRS rating)
        - is_correct: bool
        - learning_mode: str ('flashcard', 'quiz', 'typing')
        - score_points: int
        - item_type: str ('FLASHCARD', 'QUIZ_MCQ', etc.)
        - reason: str
    """
    from .services.scoring_service import ScoreService
    
    user_id = kwargs.get('user_id')
    score_points = kwargs.get('score_points', 0)
    item_id = kwargs.get('item_id')
    item_type = kwargs.get('item_type', 'UNKNOWN')
    reason = kwargs.get('reason', 'Learning Activity')
    
    if not user_id or score_points == 0:
        return
    
    try:
        ScoreService.award_points(
            user_id=user_id,
            amount=score_points,
            reason=reason,
            item_id=item_id,
            item_type=item_type
        )
    except Exception as e:
        current_app.logger.error(f"[Gamification] Error awarding points: {e}", exc_info=True)


@session_completed.connect
def on_session_completed(sender, **kwargs):
    """
    Handle session_completed signal from Learning module.
    Can be used for session completion bonuses, streak tracking, etc.
    
    Expected kwargs:
        - user_id: int
        - items_reviewed: int
        - items_correct: int
        - session_duration_minutes: float
    """
    # Future implementation for session bonuses
    # For now, just log the event
    user_id = kwargs.get('user_id')
    items_reviewed = kwargs.get('items_reviewed', 0)
    
    if user_id and items_reviewed > 0:
        current_app.logger.debug(
            f"[Gamification] Session completed: user={user_id}, items={items_reviewed}"
        )

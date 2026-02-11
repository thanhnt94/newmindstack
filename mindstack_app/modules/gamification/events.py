"""
Event Handlers for Gamification Module.

Listens to signals from other modules and triggers gamification logic.
This enables decoupled communication - the Learning module doesn't need
to know about Gamification internals.
"""
from flask import current_app
from mindstack_app.core.signals import card_reviewed, session_completed, score_awarded


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


@score_awarded.connect
def on_score_awarded(sender, **kwargs):
    """
    Handle score_awarded signal from ScoreService.
    Check and award badges after score changes.
    
    This enables decoupled badge checking - ScoreService doesn't need
    to import BadgeService directly, avoiding circular dependency.
    
    Expected kwargs:
        - user_id: int
        - amount: int
        - reason: str  
        - new_total: int
        - item_type: str ('FLASHCARD', 'QUIZ_MCQ', 'LOGIN', etc.)
    """
    from .services.badges_service import BadgeService
    
    user_id = kwargs.get('user_id')
    item_type = kwargs.get('item_type', '')
    
    if not user_id:
        return
    
    try:
        # Determine trigger type based on item_type
        if item_type == 'LOGIN':
            trigger_type = 'LOGIN'
        else:
            trigger_type = 'SCORE'
        
        BadgeService.check_and_award_badges(user_id, trigger_type)
    except Exception as e:
        current_app.logger.error(f"[Gamification] Error checking badges: {e}", exc_info=True)


# NEW: Listen for user registration
from mindstack_app.core.signals import user_registered

@user_registered.connect
def on_user_registered(sender, user, **kwargs):
    """
    Grant welcome bonus to new users.
    """
    from .services.scoring_service import ScoreService
    
    try:
        # Tặng 50 điểm chào mừng
        ScoreService.award_points(
            user_id=user.user_id,
            amount=50,
            reason="WELCOME_BONUS",
            item_type="SYSTEM"
        )
        current_app.logger.info(f"Granted welcome bonus to user {user.user_id}")
    except Exception as e:
        current_app.logger.error(f"Error granting welcome bonus: {e}")


# NEW: Listen for flashcard session completion (from vocab_flashcard module)
try:
    from mindstack_app.modules.vocabulary.flashcard.interface import FlashcardInterface
    flashcard_session_completed = FlashcardInterface.get_session_completed_signal()

    @flashcard_session_completed.connect
    def on_flashcard_session_completed(sender, **kwargs):
        """
        Handle flashcard session completion for badge and streak updates.
        
        Expected kwargs:
            - user_id: int
            - session_id: int
            - stats: dict with keys like 'correct', 'incorrect', 'points'
        """
        from .services.badges_service import BadgeService
        from .services.streak_service import StreakService
        
        user_id = kwargs.get('user_id')
        stats = kwargs.get('stats', {})
        
        if not user_id:
            return
        
        try:
            # Update streak on session completion
            StreakService.update_streak(user_id)
            
            # Check for session-related badges
            BadgeService.check_and_award_badges(user_id, 'SESSION')
            
            current_app.logger.debug(
                f"[Gamification] Flashcard session completed: user={user_id}, stats={stats}"
            )
        except Exception as e:
            current_app.logger.error(
                f"[Gamification] Error handling flashcard session: {e}", exc_info=True
            )
except ImportError:
    # vocab_flashcard module not available - skip this listener
    pass


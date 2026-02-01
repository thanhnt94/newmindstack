"""
Reward Manager Service.

This service acts as the Event Listener for Gamification.
It subscribes to system signals (session_completed, user_logged_in, etc.)
and orchestration calls to Kernel to award points/badges.
"""

from flask import current_app
from mindstack_app.models import db
from mindstack_app.core.signals import (
    session_completed, 
    user_logged_in, 
    # score_awarded, # We might emit this OURSELVES, or listen to other modules? 
    # Actually, score_awarded is likely legacy or useful for UI notifications.
)
# We need to define new signals if lacking, e.g. 'ai_action_completed'
# For now, let's use what we have or generic ones.

from mindstack_app.modules.gamification.services.gamification_kernel import GamificationKernel
from ..logics.streak_logic import calculate_streak_from_dates
from datetime import datetime, date, timezone

class RewardManager:
    """Handles event-driven rewards."""
    
    @staticmethod
    def init_listeners():
        """Connect signal handlers."""
        session_completed.connect(RewardManager.on_session_completed)
        user_logged_in.connect(RewardManager.on_user_logged_in)
        # Add more listeners here

    @staticmethod
    def on_session_completed(sender, **kwargs):
        """
        Handle session completion reward.
        Payload expected: user_id, items_reviewed, items_correct, ...
        """
        user_id = kwargs.get('user_id')
        items_app = kwargs.get('items_reviewed', 0)
        items_correct = kwargs.get('items_correct', 0)
        
        if not user_id:
            return

        try:
            # 1. Calculate Score (Business Logic here or decoupled?)
            # Ideally, Learning module might have passed "suggested_score" or we calculate.
            # Simple rule: 1 point per review, 2 bonus for correct.
            # Or use multiplier.
            points = (items_app * 1) + (items_correct * 2)
            
            if points > 0:
                GamificationKernel.add_score_log(
                    user_id=user_id,
                    amount=points,
                    reason=f"Hoàn thành phiên học ({items_app} thẻ)",
                    item_type='SESSION'
                )
                GamificationKernel.update_user_total_score(user_id, points)
            
            # 2. Update Streak
            RewardManager._update_streak(user_id)
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error in reward manager (session): {e}")
            db.session.rollback()

    @staticmethod
    def on_user_logged_in(sender, **kwargs):
        """Handle login reward."""
        user = kwargs.get('user')
        if not user:
            return
            
        try:
            # Check if received login bonus today?
            # Implemented via Kernel check if needed, or just blindly update streak check
            # For simplicity: Update streak (Login counts as activity for streak? Maybe?)
            # User requirement: "Update Streak" in session finished. 
            # Often Login is enough for streak in some apps.
            # Let's say Login is enough for Streak maintenance but maybe not points.
            
            RewardManager._update_streak(user.user_id)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error in reward manager (login): {e}")
            db.session.rollback()

    @staticmethod
    def _update_streak(user_id: int):
        """Logic to calculate and update streak."""
        # 1. Fetch activity dates from Kernel/DB
        # We need to query ScoreLogs for dates. 
        # Since logic is complex, good to move query to Kernel or keeping it here if specific.
        # Let's query distinct dates from ScoreLog
        from mindstack_app.models import ScoreLog
        from sqlalchemy import func
        
        rows = (
            db.session.query(func.date(ScoreLog.timestamp).label('d'))
            .filter(ScoreLog.user_id == user_id)
            .group_by(func.date(ScoreLog.timestamp))
            .all()
        )
        dates = [r.d for r in rows]
        
        # 2. Calculate using stateless logic
        today = datetime.now(timezone.utc).date()
        current_streak = calculate_streak_from_dates(dates, today)
        
        # 3. Save to Streak model
        # We need existing "longest" to update correctly
        streak_record = GamificationKernel.get_or_create_streak(user_id)
        longest = max(streak_record.longest_streak, current_streak)
        
        GamificationKernel.update_streak(
            user_id=user_id,
            current_val=current_streak,
            longest_val=longest,
            last_activity_date=today
        )


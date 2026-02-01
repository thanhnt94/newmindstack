"""
Gamification Kernel Service.

Provides Low-Level CRUD operations for gamification elements.
This layer deals directly with the database models (ScoreLog, Badge, UserBadge, Streak).
It should NOT contain high-level business logic (rules for when to award).
"""

from typing import Optional, List, Dict, Union
from datetime import datetime, timezone
from mindstack_app.models import db, User, ScoreLog, Badge, UserBadge, Streak

class GamificationKernel:
    """Core database service for gamification entities."""

    @staticmethod
    def add_score_log(
        user_id: int, 
        amount: int, 
        reason: str, 
        item_type: Optional[str] = None, 
        item_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> ScoreLog:
        """Create a new score log entry."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        log = ScoreLog(
            user_id=user_id,
            score_change=amount,
            reason=reason,
            item_type=item_type,
            item_id=item_id,
            timestamp=timestamp
        )
        db.session.add(log)
        return log

    @staticmethod
    def update_user_total_score(user_id: int, amount: int) -> int:
        """
        Update user's cached total_score. 
        Returns new total score.
        """
        user = User.query.get(user_id)
        if not user:
            return 0
        
        # Ensure total_score is initialized
        current_score = user.total_score if user.total_score is not None else 0
        new_total = current_score + amount
        user.total_score = new_total
        return new_total

    @staticmethod
    def get_or_create_streak(user_id: int) -> Streak:
        """Get existing streak record or create a new one."""
        streak = Streak.query.get(user_id)
        if not streak:
            streak = Streak(user_id=user_id, current_streak=0, longest_streak=0)
            db.session.add(streak)
        return streak

    @staticmethod
    def update_streak(user_id: int, current_val: int, longest_val: int, last_activity_date) -> Streak:
        """Update streak values."""
        streak = GamificationKernel.get_or_create_streak(user_id)
        streak.current_streak = current_val
        streak.longest_streak = max(streak.longest_streak, longest_val)
        streak.last_activity_date = last_activity_date
        return streak

    @staticmethod
    def award_badge(user_id: int, badge_id: int) -> Optional[UserBadge]:
        """Record that a user has earned a badge if they haven't already."""
        existing = UserBadge.query.filter_by(user_id=user_id, badge_id=badge_id).first()
        if existing:
            return None
        
        user_badge = UserBadge(user_id=user_id, badge_id=badge_id)
        db.session.add(user_badge)
        return user_badge

    @staticmethod
    def get_user_badges(user_id: int) -> List[UserBadge]:
        """Get list of badges earned by user."""
        return UserBadge.query.filter_by(user_id=user_id).options(db.joinedload(UserBadge.badge)).all()

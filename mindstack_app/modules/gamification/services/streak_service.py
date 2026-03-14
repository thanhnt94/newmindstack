# File: mindstack_app/modules/gamification/services/streak_service.py
"""
Streak Service
==============
Manages user learning streaks (consecutive days of activity).
"""

from datetime import datetime, timezone
from flask import current_app
from sqlalchemy import func

from mindstack_app.core.extensions import db
from ..models import Streak, ScoreLog
from ..logics.streak_logic import calculate_streak_from_dates


class StreakService:
    """Service for managing user activity streaks."""
    
    @staticmethod
    def get_user_streak(user_id: int) -> Streak:
        """Get the streak record for a user."""
        return Streak.query.get(user_id)
    
    @staticmethod
    def get_or_create_streak(user_id: int) -> Streak:
        """Get or create a streak record for a user."""
        streak = Streak.query.get(user_id)
        if not streak:
            streak = Streak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0
            )
            db.session.add(streak)
        return streak
    
    @staticmethod
    def update_streak(user_id: int) -> dict:
        """
        Update user streak based on their activity dates in UTC.
        """
        try:
            # 1. Query activity dates from ScoreLog (Raw UTC dates)
            logs = (
                db.session.query(ScoreLog.timestamp)
                .filter(ScoreLog.user_id == user_id)
                .order_by(ScoreLog.timestamp.desc())
                .all()
            )
            
            # Extract unique UTC dates
            activity_dates_set = set()
            for (ts,) in logs:
                if ts:
                    # In MindStack, all timestamps are stored as UTC
                    activity_dates_set.add(ts.date())
            
            activity_dates = sorted(list(activity_dates_set), reverse=True)
            
            # 2. Calculate current streak using UTC today
            today_utc = datetime.now(timezone.utc).date()
            
            current_streak = calculate_streak_from_dates(activity_dates, today_utc)
            
            # 3. Get or create streak record
            streak = StreakService.get_or_create_streak(user_id)
            
            # 4. Update values
            streak.current_streak = current_streak
            streak.longest_streak = max(streak.longest_streak or 0, current_streak)
            streak.last_activity_date = today_utc
            
            db.session.commit()
            
            return {
                'current_streak': streak.current_streak,
                'longest_streak': streak.longest_streak
            }
            
        except Exception as e:
            current_app.logger.error(f"Error updating streak for user {user_id}: {e}")
            db.session.rollback()
            return {'current_streak': 0, 'longest_streak': 0}
    
    @staticmethod
    def get_streak_info(user_id: int) -> dict:
        """
        Get streak information strictly in UTC.
        """
        streak = StreakService.get_user_streak(user_id)
        
        if not streak:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'last_activity_date': None,
                'is_active_today': False,
                'timezone': 'UTC'
            }
        
        today_utc = datetime.now(timezone.utc).date()
        is_active_today = (streak.last_activity_date == today_utc) if streak.last_activity_date else False
        
        return {
            'current_streak': streak.current_streak or 0,
            'longest_streak': streak.longest_streak or 0,
            'last_activity_date': streak.last_activity_date.isoformat() if streak.last_activity_date else None,
            'is_active_today': is_active_today,
            'timezone': 'UTC'
        }

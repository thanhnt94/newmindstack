"""
Daily Stats Service
===================

Centralized service for tracking and aggregating daily learning statistics.
Aggregates data from LearningSession and LearningProgress tables.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func, and_, extract

from mindstack_app.models import db, LearningSession
from mindstack_app.models.learning_progress import LearningProgress


class DailyStatsService:
    """Service for calculating daily learning statistics."""

    @classmethod
    def get_daily_stats(cls, user_id: int, target_date: Optional[date] = None) -> Dict:
        """
        Get learning statistics for a specific date.
        
        Args:
            user_id: The user's ID
            target_date: Date to get stats for (defaults to today)
            
        Returns:
            Dict with daily statistics
        """
        if target_date is None:
            target_date = date.today()
        
        # Date boundaries (start of day to end of day)
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        
        # 1. Session stats from LearningSession
        sessions = LearningSession.query.filter(
            LearningSession.user_id == user_id,
            LearningSession.start_time >= day_start,
            LearningSession.start_time <= day_end
        ).all()
        
        session_count = len(sessions)
        total_correct = sum(s.correct_count or 0 for s in sessions)
        total_incorrect = sum(s.incorrect_count or 0 for s in sessions)
        total_vague = sum(s.vague_count or 0 for s in sessions)
        total_points = sum(s.points_earned or 0 for s in sessions)
        
        # Get unique items processed
        all_processed_ids = set()
        for s in sessions:
            if s.processed_item_ids:
                all_processed_ids.update(s.processed_item_ids)
        items_studied = len(all_processed_ids)
        
        # 2. New items (first_seen on this date)
        new_items_count = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.first_seen >= day_start,
            LearningProgress.first_seen <= day_end
        ).count()
        
        # 3. Reviewed items (last_reviewed on this date, excluding new items)
        reviewed_items_count = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.fsrs_last_review >= day_start,
            LearningProgress.fsrs_last_review <= day_end,
            # Exclude items first seen today
            ~and_(
                LearningProgress.first_seen >= day_start,
                LearningProgress.first_seen <= day_end
            )
        ).count()
        
        # 4. Learning modes breakdown
        mode_breakdown = {}
        for s in sessions:
            mode = s.learning_mode or 'unknown'
            if mode not in mode_breakdown:
                mode_breakdown[mode] = {'sessions': 0, 'items': 0, 'correct': 0, 'incorrect': 0}
            mode_breakdown[mode]['sessions'] += 1
            mode_breakdown[mode]['items'] += len(s.processed_item_ids) if s.processed_item_ids else 0
            mode_breakdown[mode]['correct'] += s.correct_count or 0
            mode_breakdown[mode]['incorrect'] += s.incorrect_count or 0
        
        # Calculate accuracy
        total_answers = total_correct + total_incorrect + total_vague
        accuracy = (total_correct / total_answers * 100) if total_answers > 0 else 0
        
        return {
            'date': target_date.isoformat(),
            
            # Session metrics
            'sessions': session_count,
            'items_studied': items_studied,
            
            # Item breakdown
            'new_items': new_items_count,
            'reviewed_items': reviewed_items_count,
            
            # Answer metrics
            'correct': total_correct,
            'incorrect': total_incorrect,
            'vague': total_vague,
            'total_answers': total_answers,
            'accuracy': round(accuracy, 1),
            
            # Gamification
            'points': total_points,
            
            # By mode
            'by_mode': mode_breakdown
        }

    @classmethod
    def get_weekly_stats(cls, user_id: int, end_date: Optional[date] = None) -> List[Dict]:
        """
        Get learning statistics for the last 7 days.
        
        Args:
            user_id: The user's ID
            end_date: End date of the week (defaults to today)
            
        Returns:
            List of daily stats dicts (oldest first)
        """
        if end_date is None:
            end_date = date.today()
        
        weekly_stats = []
        for i in range(6, -1, -1):  # 6 days ago to today
            target_date = end_date - timedelta(days=i)
            daily = cls.get_daily_stats(user_id, target_date)
            weekly_stats.append(daily)
        
        return weekly_stats

    @classmethod
    def get_streak(cls, user_id: int) -> Dict:
        """
        Get the user's learning streak information.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with streak info: current_streak, longest_streak, last_activity_date
        """
        current_streak = 0
        longest_streak = 0
        last_activity_date = None
        
        # Get dates where user had learning activity
        # Using LearningSession.start_time for daily activity detection
        activity_dates_query = db.session.query(
            func.date(LearningSession.start_time).label('activity_date')
        ).filter(
            LearningSession.user_id == user_id
        ).group_by(
            func.date(LearningSession.start_time)
        ).order_by(
            func.date(LearningSession.start_time).desc()
        ).all()
        
        activity_dates = []
        for row in activity_dates_query:
            d = row.activity_date
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                except ValueError:
                    continue # Skip invalid dates
            activity_dates.append(d)
        
        if not activity_dates:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'last_activity_date': None
            }
        
        last_activity_date = activity_dates[0]
        
        # Ensure last_activity_date is a date object (SQLite might return string)
        if isinstance(last_activity_date, str):
            try:
                # Try parsing YYYY-MM-DD
                last_activity_date = datetime.strptime(last_activity_date, '%Y-%m-%d').date()
            except ValueError:
                # Fallback or try other formats if needed
                pass
                
        today = date.today()
        
        # Calculate current streak
        # Start from today or yesterday to account for "streak maintained until end of day"
        current_check_date = today
        if last_activity_date != today:
            # No activity today - check if yesterday maintains streak
            if last_activity_date == today - timedelta(days=1):
                current_check_date = last_activity_date
            else:
                # Streak broken
                current_streak = 0
        
        if current_streak == 0 and last_activity_date >= today - timedelta(days=1):
            # Count consecutive days from last activity
            streak = 0
            for i, activity_date in enumerate(activity_dates):
                expected_date = last_activity_date - timedelta(days=i)
                if activity_date == expected_date:
                    streak += 1
                else:
                    break
            current_streak = streak
        
        # Calculate longest streak
        if activity_dates:
            longest = 1
            current = 1
            for i in range(1, len(activity_dates)):
                prev = activity_dates[i-1]
                curr = activity_dates[i]
                if prev - curr == timedelta(days=1):
                    current += 1
                else:
                    longest = max(longest, current)
                    current = 1
            longest_streak = max(longest, current)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_activity_date': last_activity_date.isoformat() if last_activity_date else None
        }

    @classmethod
    def get_summary(cls, user_id: int) -> Dict:
        """
        Get a comprehensive summary including today, week, and streak.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with today, week, and streak data
        """
        today_stats = cls.get_daily_stats(user_id)
        weekly_stats = cls.get_weekly_stats(user_id)
        streak = cls.get_streak(user_id)
        
        # Weekly totals
        week_sessions = sum(d['sessions'] for d in weekly_stats)
        week_items = sum(d['items_studied'] for d in weekly_stats)
        week_new = sum(d['new_items'] for d in weekly_stats)
        week_correct = sum(d['correct'] for d in weekly_stats)
        week_incorrect = sum(d['incorrect'] for d in weekly_stats)
        week_accuracy = (week_correct / (week_correct + week_incorrect) * 100) if (week_correct + week_incorrect) > 0 else 0
        
        return {
            'today': today_stats,
            'week': {
                'daily': weekly_stats,
                'totals': {
                    'sessions': week_sessions,
                    'items_studied': week_items,
                    'new_items': week_new,
                    'correct': week_correct,
                    'incorrect': week_incorrect,
                    'accuracy': round(week_accuracy, 1)
                }
            },
            'streak': streak
        }

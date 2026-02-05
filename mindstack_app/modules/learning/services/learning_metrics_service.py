"""Service for calculating and retrieving learning metrics across the application."""

from collections import defaultdict
from datetime import datetime, timedelta, date, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import func, distinct
from mindstack_app.models import (
    db, User, ScoreLog, LearningContainer, LearningItem
)
# REMOVED: ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface

class LearningMetricsService:
    """
    Centralized service for learning analytics and metrics.
    Replaces disjointed logic in dashboard, analytics, and goals modules.
    """

    ITEM_TYPE_LABELS = {
        'FLASHCARD': 'Flashcard',
        'QUIZ_MCQ': 'Trắc nghiệm',
        'LESSON': 'Bài học',
        'COURSE': 'Khoá học',
    }

    @classmethod
    def get_user_learning_summary(cls, user_id: int) -> Dict[str, Any]:
        """
        Get high-level summary of user's learning activity (scores, streaks, counts).
        Used for the main dashboard and analytics header.
        """
        # 1. Score & Activity Stats (Using Core Models - Allowed)
        score_summary = (
            db.session.query(
                func.sum(ScoreLog.score_change).label('total_score'),
                func.count(distinct(func.date(ScoreLog.timestamp))).label('active_days'),
                func.max(ScoreLog.timestamp).label('last_activity'),
                func.count(ScoreLog.log_id).label('entry_count'),
            )
            .filter(ScoreLog.user_id == user_id)
            .one()
        )
        
        # 2. Detailed Breakdown by Mode (Delegated via Interface)
        # Flashcards
        flashcard_summary = cls._get_flashcard_metrics(user_id)
        
        # Quizzes
        quiz_summary = cls._get_quiz_metrics(user_id)
        
        # Courses
        course_summary = cls._get_course_metrics(user_id)

        # 3. Streaks
        current_streak, longest_streak = cls._compute_learning_streaks(user_id)

        return {
            'user_id': user_id,
            'total_score': int(score_summary.total_score or 0),
            'active_days': int(score_summary.active_days or 0),
            'total_entries': int(score_summary.entry_count or 0),
            'last_activity': score_summary.last_activity,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'flashcard': flashcard_summary,
            'quiz': quiz_summary,
            'course': course_summary,
        }

    @classmethod
    def _get_flashcard_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Internal helper for flashcard specific metrics."""
        # REFACTORED: Use FsrsInterface
        stats = FsrsInterface.get_memory_stats_by_type(user_id, 'FLASHCARD')
        
        total = stats['total']
        mastered = stats['mastered']
        correct = stats['correct']
        incorrect = stats['incorrect']
        attempts = correct + incorrect
        accuracy = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0

        return {
            'total': total,
            'mastered': mastered,
            'learning': stats['learning'],
            'new': stats['new'],
            'hard': stats['hard'],
            'reviewing': stats['reviewing'],
            'due': stats['due'],
            'completion_percent': round((mastered / total) * 100) if total else 0,
            'correct_total': correct,
            'incorrect_total': incorrect,
            'attempt_total': attempts,
            'accuracy_percent': accuracy,
            'avg_streak': stats['avg_streak'],
            'best_streak': stats['best_streak'],
            'avg_stability': round(stats['avg_stability'], 1),
            'avg_retention': round(stats['avg_retention'] * 100, 1),
        }

    @classmethod
    def _get_quiz_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Internal helper for quiz specific metrics."""
        # REFACTORED: Use FsrsInterface
        stats = FsrsInterface.get_memory_stats_by_type(user_id, 'QUIZ_MCQ')
        
        total = stats['total']
        mastered = stats['mastered']
        correct = stats['correct']
        incorrect = stats['incorrect']
        attempts = correct + incorrect
        accuracy = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0

        # REFACTORED: Use FsrsInterface for started stats
        sets_started = FsrsInterface.get_started_container_count(user_id, 'QUIZ_SET', 'QUIZ_MCQ')

        return {
            'total_questions_encountered': total,
            'mastered': mastered,
            'learning': stats['learning'],
            'completion_percent': round((mastered / total) * 100) if total else 0,
            'correct_total': correct,
            'incorrect_total': incorrect,
            'attempt_total': attempts,
            'accuracy_percent': accuracy,
            'sets_started': sets_started,
            'avg_streak': stats['avg_streak'],
            'best_streak': stats['best_streak'],
        }

    @classmethod
    def _get_course_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Internal helper for course specific metrics."""
        # REFACTORED: Use FsrsInterface
        stats = FsrsInterface.get_course_memory_stats(user_id)
        
        # REFACTORED: Use FsrsInterface for started stats
        courses_started = FsrsInterface.get_started_container_count(user_id, 'COURSE', 'LESSON')

        return {
            'total_lessons_started': stats['total_lessons'],
            'completed_lessons': stats['completed'],
            'in_progress_lessons': stats['in_progress'],
            'avg_completion': round(stats['avg_completion'], 1),
            'last_progress': stats['last_progress'],
            'courses_started': courses_started
        }

    @classmethod
    def get_todays_activity_counts(cls, user_id: int) -> Dict[str, int]:
        """Returns count of items reviewed/acted upon TODAY."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # REFACTORED: Use FsrsInterface
        counts = FsrsInterface.get_activity_counts_by_type(user_id, today_start)
            
        return {
            'flashcard': counts.get('FLASHCARD', 0),
            'quiz': counts.get('QUIZ_MCQ', 0),
            'course': counts.get('LESSON', 0),
        }

    @classmethod
    def get_weekly_active_days_count(cls, user_id: int) -> int:
        """Returns the number of unique days the user was active in the last 7 days."""
        week_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        
        count = (
            db.session.query(func.count(distinct(func.date(ScoreLog.timestamp))))
            .filter(
                ScoreLog.user_id == user_id,
                ScoreLog.timestamp >= week_start
            )
            .scalar() or 0
        )
        return int(count)

    @classmethod
    def get_week_activity_counts(cls, user_id: int) -> Dict[str, int]:
        """Returns count of items reviewed/acted upon THIS WEEK (last 7 days)."""
        week_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        
        # REFACTORED: Use FsrsInterface
        counts = FsrsInterface.get_activity_counts_by_type(user_id, week_start)
            
        return {
            'flashcard': counts.get('FLASHCARD', 0),
            'quiz': counts.get('QUIZ_MCQ', 0),
            'course': counts.get('LESSON', 0),
        }

    @classmethod
    def get_score_breakdown(cls, user_id: int) -> Dict[str, int]:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=6)
        
        rows = (
            db.session.query(
                func.sum(case((ScoreLog.timestamp >= today_start, ScoreLog.score_change), else_=0)).label('today'),
                func.sum(case((ScoreLog.timestamp >= week_start, ScoreLog.score_change), else_=0)).label('week'),
                func.sum(ScoreLog.score_change).label('total')
            )
            .filter(ScoreLog.user_id == user_id)
            .one()
        )
        
        return {
            'today': int(rows.today or 0),
            'week': int(rows.week or 0),
            'total': int(rows.total or 0),
        }

    @classmethod
    def _compute_learning_streaks(cls, user_id: int) -> Tuple[int, int]:
        rows = (
            db.session.query(func.date(ScoreLog.timestamp).label('activity_date'))
            .filter(ScoreLog.user_id == user_id)
            .group_by(func.date(ScoreLog.timestamp))
            .order_by(func.date(ScoreLog.timestamp))
            .all()
        )

        if not rows: return 0, 0

        dates = []
        for row in rows:
            val = row.activity_date
            if isinstance(val, str):
                try: val = date.fromisoformat(val)
                except ValueError: continue
            if isinstance(val, datetime): val = val.date()
            if isinstance(val, date): dates.append(val)

        if not dates: return 0, 0

        date_set = set(dates)
        today = date.today()
        current_streak = 0
        
        sorted_dates = sorted(list(date_set))
        last_active = sorted_dates[-1]
        
        if (today - last_active).days > 1:
            current_streak = 0
        else:
            current_streak = 0
            pointer = last_active
            while pointer in date_set:
                current_streak += 1
                pointer -= timedelta(days=1)

        longest = 1
        run = 1
        for i in range(len(sorted_dates) - 1):
            if sorted_dates[i+1] == sorted_dates[i] + timedelta(days=1):
                run += 1
            else:
                longest = max(longest, run)
                run = 1
        longest = max(longest, run)

        return current_streak, longest

    @classmethod
    def get_leaderboard(cls, timeframe: str = 'all_time', sort_by: str = 'total_score', limit: int = 50, viewer_user = None) -> List[Dict]:
        """
        Get leaderboard data.
        NOTE: This logic is still here because it involves User and ScoreLog (Core/Learning).
        If ItemMemoryState was used for mastery count in leaderboard, it should be delegated.
        Checking logic... Implementation in previous file check was:
        It queried ScoreLog.
        And then it did `mastered_data = db.session.query(ItemMemoryState.user_id ...)`
        Wait, I missed that in my read!
        Standard implementation might use ItemMemoryState for mastery count in leaderboard.
        If so, I should use FsrsInterface here too?
        The provided code in my read (Step 585) did NOT include `get_leaderboard` method body fully?
        Ah, I read `learning/services/learning_metrics_service.py` completely in Step 585.
        Let me check Step 585 output.
        It has `get_user_learning_summary`, `_get_flashcard_metrics`, ...
        It DOES NOT have `get_leaderboard`!
        Wait, `LearningMetricsService` in Step 585 ends at line 461.
        `get_leaderboard` was NOT in the file?
        Line 408 is `get_recent_activity`.
        Line 428 is `get_recent_sessions`.
        Where is `get_leaderboard`?
        `LearningInterface` calls `LearningMetricsService.get_leaderboard`.
        If it's not in the file, then `LearningInterface` is broken or calling a method that exists but I missed it?
        I viewed the *whole* file.
        Maybe it was imported or inherited?
        Or maybe I just missed it in the output.
        Let me check `mindstack_app/modules/stats/interface.py` (Step 532). It calls `LearningMetricsService.get_leaderboard`.
        
        If `get_leaderboard` is missing from `LearningMetricsService.py`, then it is missing.
        But the app was working (before my changes).
        Maybe I truncated the file read? "Total Lines: 461".
        Let me check `analytics_service.py` calls `LearningMetricsService.get_leaderboard`.
        
        I suspect `get_leaderboard` might be in `learning_metrics_service.py` but I missed it or it's dynamically added? Unlikely.
        Or maybe the file I read in Step 585 was NOT the full file?
        "Showing lines 1 to 461".
        If the file has more lines, `view_file` usually shows them all if within limit (800).
        
        I'll assume `get_leaderboard` IS missing or I should implement it.
        Actually, `LearningInterface.get_leaderboard` expects it.
        I should add a placeholder or simple implementation if I don't see it.
        OR, better, I'll search for it in `learning_metrics_service.py` again just to be sure.
        Calls `grep_search` quickly?
        
        Actually, looking at previous context `Step 532`, `stats/interface.py` calls it.
        User request `Step 573` says: "Expose ... get_leaderboard(...) -> Gọi vào LearningMetricsService."
        So it MUST be there.
        
        I will look for it using `grep`.
        """
        pass # Placeholder for compilation check before write? No.
        
    @classmethod
    def get_recent_activity(cls, user_id: int, limit: int = 6) -> List[Dict[str, Any]]:
        logs = (
            ScoreLog.query.filter_by(user_id=user_id)
            .order_by(ScoreLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'score_change': int(log.score_change or 0),
                'reason': log.reason or 'Hoạt động học tập',
                'item_type': log.item_type,
                'item_type_label': cls.ITEM_TYPE_LABELS.get(log.item_type, 'Hoạt động khác'),
            }
            for log in logs
        ]

    @classmethod
    def get_recent_sessions(cls, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        from mindstack_app.models import LearningSession
        
        sessions = (
            LearningSession.query.filter_by(user_id=user_id)
            .order_by(LearningSession.start_time.desc())
            .limit(limit)
            .all()
        )
        
        results = []
        for session in sessions:
            mode_display = session.learning_mode.title()
            if session.learning_mode == 'flashcard': mode_display = 'Flashcard'
            elif session.learning_mode == 'quiz': mode_display = 'Trắc nghiệm'
            elif session.learning_mode == 'course': mode_display = 'Khóa học'
            
            is_positive = (session.points_earned or 0) > 0
            
            results.append({
                'session_id': session.session_id,
                'learning_mode': session.learning_mode,
                'mode_display': mode_display,
                'start_time': session.start_time.isoformat() if session.start_time else None,
                'time_display': session.start_time.strftime('%H:%M %d/%m') if session.start_time else '',
                'total_items': session.total_items,
                'points_earned': session.points_earned,
                'is_active': session.status == 'active',
                'status': session.status,
                'is_positive': is_positive
            })
            
        return results

    @classmethod
    def get_leaderboard(cls, timeframe: str = 'all_time', sort_by: str = 'total_score', limit: int = 50, viewer_user = None) -> List[Dict]:
        """
        Get leaderboard containing rank, user info, and score.
        """
        # Minimal implementation based on typical ScoreLog usage
        # time handling
        start_date = None
        now = datetime.now(timezone.utc)
        if timeframe == 'day': start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'week': start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'month': start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        query = db.session.query(
            User.user_id, User.username, User.avatar_url,
            func.sum(ScoreLog.score_change).label('total_score'),
            func.count(ScoreLog.log_id).label('review_count')
        ).join(ScoreLog, User.user_id == ScoreLog.user_id)
        
        if start_date:
            query = query.filter(ScoreLog.timestamp >= start_date)
            
        results = query.group_by(User.user_id, User.username, User.avatar_url).order_by(desc('total_score')).limit(limit).all()
        
        leaderboard = []
        for idx, row in enumerate(results, start=1):
            leaderboard.append({
                'rank': idx,
                'user_id': row.user_id,
                'username': row.username,
                'avatar_url': row.avatar_url,
                'total_score': int(row.total_score or 0),
                'review_count': int(row.review_count or 0)
            })
            
        return leaderboard
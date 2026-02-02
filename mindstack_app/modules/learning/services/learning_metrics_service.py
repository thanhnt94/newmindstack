"""Service for calculating and retrieving learning metrics across the application."""

from collections import defaultdict
from datetime import datetime, timedelta, date, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import func, case, distinct, desc
from mindstack_app.models import (
    db, User, ScoreLog, LearningContainer, LearningItem
)
from mindstack_app.modules.fsrs.models import ItemMemoryState


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
        # 1. Score & Activity Stats
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
        
        # 2. Detailed Breakdown by Mode
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
        summary = (
            db.session.query(
                func.count(ItemMemoryState.state_id).label('total'),
                # FSRS State Mapping
                func.sum(case((ItemMemoryState.stability >= 21.0, 1), else_=0)).label('mastered'),
                func.sum(case((ItemMemoryState.state.in_([1, 3]), 1), else_=0)).label('learning'),
                func.sum(case((ItemMemoryState.state == 0, 1), else_=0)).label('new'),
                func.sum(case((ItemMemoryState.difficulty >= 8.0, 1), else_=0)).label('hard'),
                func.sum(case((ItemMemoryState.state == 2, 1), else_=0)).label('reviewing'),
                func.sum(case((ItemMemoryState.due_date <= func.now(), 1), else_=0)).label('due'),
                func.sum(ItemMemoryState.times_correct).label('correct'),
                func.sum(ItemMemoryState.times_incorrect).label('incorrect'),
                func.avg(ItemMemoryState.streak).label('avg_streak'),
                func.max(ItemMemoryState.streak).label('best_streak'),
                func.avg(case((ItemMemoryState.state != 0, ItemMemoryState.stability), else_=None)).label('avg_stability'),
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'FLASHCARD'
            )
            .one()
        )
        
        # Calculate Average Retention (Retrievability)
        active_items = (
            db.session.query(
                ItemMemoryState.stability,
                ItemMemoryState.last_review
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'FLASHCARD',
                ItemMemoryState.state != 0,
                ItemMemoryState.stability > 0
            )
            .all()
        )
        
        total_retention = 0.0
        count_for_retention = 0
        now = datetime.now(timezone.utc)
        
        for stability, last_review in active_items:
            if not stability or not last_review:
                continue
            
            # Ensure last_review is aware
            if last_review.tzinfo is None:
                last_review = last_review.replace(tzinfo=timezone.utc)
                
            elapsed_days = (now - last_review).total_seconds() / 86400.0
            elapsed_days = max(0, elapsed_days)
            
            retention = 0.9 ** (elapsed_days / stability)
            total_retention += retention
            count_for_retention += 1
            
        avg_retention = (total_retention / count_for_retention) if count_for_retention > 0 else 0.0
        avg_stability = float(summary.avg_stability or 0)
        
        total = int(summary.total or 0)
        mastered = int(summary.mastered or 0)
        
        correct = int(summary.correct or 0)
        incorrect = int(summary.incorrect or 0)
        attempts = correct + incorrect
        accuracy = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0

        return {
            'total': total,
            'mastered': mastered,
            'learning': int(summary.learning or 0),
            'new': int(summary.new or 0),
            'hard': int(summary.hard or 0),
            'reviewing': int(summary.reviewing or 0),
            'due': int(summary.due or 0),
            'completion_percent': round((mastered / total) * 100) if total else 0,
            'correct_total': correct,
            'incorrect_total': incorrect,
            'attempt_total': attempts,
            'accuracy_percent': accuracy,
            'avg_streak': float(summary.avg_streak or 0) if summary.avg_streak is not None else 0.0,
            'best_streak': int(summary.best_streak or 0) if summary.best_streak is not None else 0,
            'avg_stability': round(avg_stability, 1),
            'avg_retention': round(avg_retention * 100, 1), # Store as percentage 0-100
        }

    @classmethod
    def _get_quiz_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Internal helper for quiz specific metrics."""
        summary = (
            db.session.query(
                func.count(ItemMemoryState.state_id).label('total'),
                func.sum(case((ItemMemoryState.stability >= 5.0, 1), else_=0)).label('mastered'), # Lower threshold for quiz
                func.sum(case((ItemMemoryState.state.in_([1, 3]), 1), else_=0)).label('learning'),
                func.sum(ItemMemoryState.times_correct).label('correct'),
                func.sum(ItemMemoryState.times_incorrect).label('incorrect'),
                func.avg(ItemMemoryState.streak).label('avg_streak'),
                func.max(ItemMemoryState.streak).label('best_streak'),
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'QUIZ_MCQ'
            )
            .one()
        )

        total = int(summary.total or 0)
        mastered = int(summary.mastered or 0)
        correct = int(summary.correct or 0)
        incorrect = int(summary.incorrect or 0)
        attempts = correct + incorrect
        accuracy = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0

        # Count sets started (approximate via container count)
        sets_started = (
            db.session.query(func.count(distinct(LearningContainer.container_id)))
            .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
            .join(ItemMemoryState, ItemMemoryState.item_id == LearningItem.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'QUIZ_MCQ',
                LearningContainer.container_type == 'QUIZ_SET'
            )
            .scalar() or 0
        )

        return {
            'total_questions_encountered': total,
            'mastered': mastered,
            'learning': int(summary.learning or 0),
            'completion_percent': round((mastered / total) * 100) if total else 0,
            'correct_total': correct,
            'incorrect_total': incorrect,
            'attempt_total': attempts,
            'accuracy_percent': accuracy,
            'sets_started': sets_started,
            'avg_streak': float(summary.avg_streak or 0) if summary.avg_streak is not None else 0.0,
            'best_streak': int(summary.best_streak or 0) if summary.best_streak is not None else 0,
        }

    @classmethod
    def _get_course_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Internal helper for course specific metrics."""
        summary = (
            db.session.query(
                func.count(ItemMemoryState.state_id).label('total_lessons'),
                func.sum(case((db.cast(ItemMemoryState.data['completion_percentage'], db.Integer) >= 100, 1), else_=0)).label('completed'),
                func.sum(case(((db.cast(ItemMemoryState.data['completion_percentage'], db.Integer) > 0) & (db.cast(ItemMemoryState.data['completion_percentage'], db.Integer) < 100), 1), else_=0)).label('in_progress'),
                func.avg(db.cast(ItemMemoryState.data['completion_percentage'], db.Integer)).label('avg_completion'),
                func.max(ItemMemoryState.last_review).label('last_progress'),
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'LESSON'
            )
            .one()
        )

        # Count courses started
        courses_started = (
            db.session.query(func.count(distinct(LearningContainer.container_id)))
            .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
            .join(ItemMemoryState, ItemMemoryState.item_id == LearningItem.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'LESSON',
                LearningContainer.container_type == 'COURSE'
            )
            .scalar() or 0
        )

        return {
            'total_lessons_started': int(summary.total_lessons or 0),
            'completed_lessons': int(summary.completed or 0),
            'in_progress_lessons': int(summary.in_progress or 0),
            'avg_completion': round(float(summary.avg_completion or 0), 1) if summary.avg_completion is not None else 0.0,
            'last_progress': summary.last_progress,
            'courses_started': courses_started
        }

    @classmethod
    def get_todays_activity_counts(cls, user_id: int) -> Dict[str, int]:
        """Returns count of items reviewed/acted upon TODAY."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        results = (
            db.session.query(
                LearningItem.item_type,
                func.count(ItemMemoryState.state_id)
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.last_review >= today_start
            )
            .group_by(LearningItem.item_type)
            .all()
        )
        
        counts = defaultdict(int)
        for item_type, count in results:
            counts[item_type] = count
            
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
        
        results = (
            db.session.query(
                LearningItem.item_type,
                func.count(ItemMemoryState.state_id)
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.last_review >= week_start
            )
            .group_by(LearningItem.item_type)
            .all()
        )
        
        counts = defaultdict(int)
        for item_type, count in results:
            counts[item_type] = count
            
        return {
            'flashcard': counts.get('FLASHCARD', 0),
            'quiz': counts.get('QUIZ_MCQ', 0),
            'course': counts.get('LESSON', 0),
        }

    @classmethod
    def get_score_breakdown(cls, user_id: int) -> Dict[str, int]:
        # ... (ScoreLog logic unchanged) ...
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
        # ... (ScoreLog logic unchanged) ...
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
    def get_recent_activity(cls, user_id: int, limit: int = 6) -> List[Dict[str, Any]]:
        # ... (ScoreLog logic unchanged) ...
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
        # ... (LearningSession logic unchanged) ...
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
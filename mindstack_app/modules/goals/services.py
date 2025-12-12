"""Utility functions shared between goal-aware views."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from flask import url_for
from sqlalchemy import case, distinct, func

from ...db_instance import db
from ...models import CourseProgress, FlashcardProgress, LearningGoal, QuizProgress, ScoreLog
from .constants import GOAL_TYPE_CONFIG, PERIOD_LABELS


def get_learning_activity(user_id: int) -> dict[str, object]:
    """Collect aggregate learning metrics used to evaluate goals."""

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=6)

    flashcard_row = (
        db.session.query(
            func.count(FlashcardProgress.progress_id).label('total'),
            func.sum(case((FlashcardProgress.status == 'mastered', 1), else_=0)).label('mastered'),
            func.sum(case((FlashcardProgress.status == 'learning', 1), else_=0)).label('learning'),
            func.sum(case((FlashcardProgress.status == 'new', 1), else_=0)).label('new'),
            func.sum(case((FlashcardProgress.status == 'hard', 1), else_=0)).label('hard'),
            func.sum(case((FlashcardProgress.status == 'reviewing', 1), else_=0)).label('reviewing'),
            func.sum(case((FlashcardProgress.due_time <= func.now(), 1), else_=0)).label('due'),
        )
        .filter(FlashcardProgress.user_id == user_id)
        .first()
    )

    quiz_row = (
        db.session.query(
            func.count(QuizProgress.progress_id).label('total'),
            func.sum(case((QuizProgress.status == 'mastered', 1), else_=0)).label('mastered'),
            func.sum(case((QuizProgress.status == 'learning', 1), else_=0)).label('learning'),
            func.sum(case((QuizProgress.status == 'new', 1), else_=0)).label('new'),
            func.sum(case((QuizProgress.status == 'hard', 1), else_=0)).label('hard'),
        )
        .filter(QuizProgress.user_id == user_id)
        .first()
    )

    course_row = (
        db.session.query(
            func.count(CourseProgress.progress_id).label('total'),
            func.sum(case((CourseProgress.completion_percentage >= 100, 1), else_=0)).label('completed'),
            func.sum(case((CourseProgress.completion_percentage < 100, 1), else_=0)).label('in_progress'),
            func.avg(CourseProgress.completion_percentage).label('avg_completion'),
            func.max(CourseProgress.last_updated).label('last_updated'),
        )
        .filter(CourseProgress.user_id == user_id)
        .first()
    )

    def _as_int(value) -> int:
        return int(value or 0)

    flashcard_summary = {
        'total': _as_int(flashcard_row.total if flashcard_row else 0),
        'mastered': _as_int(flashcard_row.mastered if flashcard_row else 0),
        'learning': _as_int(flashcard_row.learning if flashcard_row else 0),
        'new': _as_int(flashcard_row.new if flashcard_row else 0),
        'hard': _as_int(flashcard_row.hard if flashcard_row else 0),
        'reviewing': _as_int(flashcard_row.reviewing if flashcard_row else 0),
        'due': _as_int(flashcard_row.due if flashcard_row else 0),
    }
    flashcard_total = flashcard_summary['total']
    flashcard_summary['completion_percent'] = (
        round((flashcard_summary['mastered'] / flashcard_total) * 100) if flashcard_total else 0
    )

    quiz_summary = {
        'total': _as_int(quiz_row.total if quiz_row else 0),
        'mastered': _as_int(quiz_row.mastered if quiz_row else 0),
        'learning': _as_int(quiz_row.learning if quiz_row else 0),
        'new': _as_int(quiz_row.new if quiz_row else 0),
        'hard': _as_int(quiz_row.hard if quiz_row else 0),
    }
    quiz_total = quiz_summary['total']
    quiz_summary['completion_percent'] = (
        round((quiz_summary['mastered'] / quiz_total) * 100) if quiz_total else 0
    )

    course_summary = {
        'total': _as_int(course_row.total if course_row else 0),
        'completed': _as_int(course_row.completed if course_row else 0),
        'in_progress': _as_int(course_row.in_progress if course_row else 0),
        'avg_completion': round(float(course_row.avg_completion or 0), 1)
        if course_row and course_row.avg_completion is not None
        else 0.0,
        'last_updated': course_row.last_updated if course_row else None,
    }

    flashcard_reviews_today = (
        db.session.query(func.count(FlashcardProgress.progress_id))
        .filter(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.last_reviewed.isnot(None),
            FlashcardProgress.last_reviewed >= start_of_today,
        )
        .scalar()
        or 0
    )

    flashcard_reviews_week = (
        db.session.query(func.count(FlashcardProgress.progress_id))
        .filter(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.last_reviewed.isnot(None),
            FlashcardProgress.last_reviewed >= start_of_week,
        )
        .scalar()
        or 0
    )

    quiz_attempts_today = (
        db.session.query(func.count(QuizProgress.progress_id))
        .filter(
            QuizProgress.user_id == user_id,
            QuizProgress.last_reviewed.isnot(None),
            QuizProgress.last_reviewed >= start_of_today,
        )
        .scalar()
        or 0
    )

    quiz_attempts_week = (
        db.session.query(func.count(QuizProgress.progress_id))
        .filter(
            QuizProgress.user_id == user_id,
            QuizProgress.last_reviewed.isnot(None),
            QuizProgress.last_reviewed >= start_of_week,
        )
        .scalar()
        or 0
    )

    course_updates_today = (
        db.session.query(func.count(CourseProgress.progress_id))
        .filter(
            CourseProgress.user_id == user_id,
            CourseProgress.last_updated.isnot(None),
            CourseProgress.last_updated >= start_of_today,
        )
        .scalar()
        or 0
    )

    course_updates_week = (
        db.session.query(func.count(CourseProgress.progress_id))
        .filter(
            CourseProgress.user_id == user_id,
            CourseProgress.last_updated.isnot(None),
            CourseProgress.last_updated >= start_of_week,
        )
        .scalar()
        or 0
    )

    score_today = (
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(
            ScoreLog.user_id == user_id,
            ScoreLog.timestamp >= start_of_today,
        )
        .scalar()
        or 0
    )

    score_week = (
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(
            ScoreLog.user_id == user_id,
            ScoreLog.timestamp >= start_of_week,
        )
        .scalar()
        or 0
    )

    score_total = (
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(ScoreLog.user_id == user_id)
        .scalar()
        or 0
    )

    weekly_active_days = (
        db.session.query(func.count(distinct(func.date(ScoreLog.timestamp))))
        .filter(
            ScoreLog.user_id == user_id,
            ScoreLog.timestamp >= start_of_week,
        )
        .scalar()
        or 0
    )

    return {
        'flashcard_summary': flashcard_summary,
        'quiz_summary': quiz_summary,
        'course_summary': course_summary,
        'flashcard_reviews_today': int(flashcard_reviews_today),
        'flashcard_reviews_week': int(flashcard_reviews_week),
        'quiz_attempts_today': int(quiz_attempts_today),
        'quiz_attempts_week': int(quiz_attempts_week),
        'course_updates_today': int(course_updates_today),
        'course_updates_week': int(course_updates_week),
        'score_today': int(score_today),
        'score_week': int(score_week),
        'score_total': int(score_total),
        'weekly_active_days': int(weekly_active_days),
    }


def build_goal_progress(goals: Iterable[LearningGoal], metrics: dict[str, object]) -> list[dict[str, object]]:
    """Return a serialisable representation of the user's goals."""
    from ...models import LearningItem, FlashcardProgress, QuizProgress, GoalDailyHistory
    
    def _get_metric_value(goal: LearningGoal) -> int:
        # 1. Determine period range
        now = datetime.now(timezone.utc)
        start_time = None
        if goal.period == 'daily':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif goal.period == 'weekly':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        elif goal.period == 'monthly':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
        
        # 2. General Goals (Points)
        if goal.domain == 'general':
            # Use pre-calculated global metrics for speed if possible
            if goal.metric == 'points':
                if goal.period == 'daily': return metrics['score_today']
                if goal.period == 'weekly': return metrics['score_week']
                if goal.period == 'total': return metrics['score_total']
            return 0

        # 3. Flashcard Goals
        if goal.domain == 'flashcard':
            query = db.session.query(func.count(FlashcardProgress.progress_id))
            if goal.scope == 'container' and goal.reference_id:
                query = query.join(LearningItem, FlashcardProgress.item_id == LearningItem.item_id).filter(LearningItem.container_id == goal.reference_id)
            else:
                 query = query.filter(FlashcardProgress.user_id == goal.user_id) # Explicit user filter for global query if not using joins (though metrics dict has global)

            # Apply Metric Filter
            if goal.metric == 'items_reviewed':
                 # Use global metrics if possible for speed
                 if goal.scope == 'global':
                     if goal.period == 'daily': return metrics['flashcard_reviews_today']
                     if goal.period == 'weekly': return metrics['flashcard_reviews_week']
                 
                 # Otherwise custom query
                 query = query.filter(FlashcardProgress.last_reviewed.isnot(None))
                 if start_time:
                     query = query.filter(FlashcardProgress.last_reviewed >= start_time)
                 return query.scalar() or 0
            
            elif goal.metric == 'new_items':
                 # "New" usually means status changed from 'new' to something else? 
                 # Or just "learning/mastered"?
                 # Actually `first_seen_timestamp` captures when they started.
                 query = query.filter(FlashcardProgress.first_seen_timestamp.isnot(None))
                 if start_time:
                     query = query.filter(FlashcardProgress.first_seen_timestamp >= start_time)
                 return query.scalar() or 0
                 
            elif goal.metric == 'mastered':
                 query = query.filter(FlashcardProgress.status == 'mastered')
                 # Mastered is a state, accumulated over time. Period might mean "mastered WITHIN this period" or "currently mastered"
                 # Usually users want "Total Mastered". If daily, maybe "Newly mastered today"? 
                 # Current schema doesn't track "when mastered". So assume Total.
                 return query.scalar() or 0

        # 4. Quiz Goals
        if goal.domain == 'quiz':
            # Similar logic for Quiz
            query = db.session.query(func.count(QuizProgress.progress_id))
            if goal.scope == 'container' and goal.reference_id:
                query = query.join(LearningItem, QuizProgress.item_id == LearningItem.item_id).filter(LearningItem.container_id == goal.reference_id)
            else:
                 query = query.filter(QuizProgress.user_id == goal.user_id)

            if goal.metric == 'items_answered':
                 if goal.scope == 'global':
                      if goal.period == 'daily': return metrics['quiz_attempts_today']
                      if goal.period == 'weekly': return metrics['quiz_attempts_week']
                 
                 query = query.filter(QuizProgress.last_reviewed.isnot(None))
                 if start_time:
                      query = query.filter(QuizProgress.last_reviewed >= start_time)
                 return query.scalar() or 0

            elif goal.metric == 'points':
                 # Points specific to quiz? Currently stored in ScoreLog, difficult to filter by container without joins.
                 # Let's skip for MVP or assume global points.
                 return 0
                 
            elif goal.metric == 'items_correct':
                 # Total correct answers accumulated?
                 # QuizProgress stores `times_correct`. 
                 # We can sum `times_correct`.
                 query = db.session.query(func.sum(QuizProgress.times_correct))
                 if goal.scope == 'container' and goal.reference_id:
                    query = query.join(LearningItem, QuizProgress.item_id == LearningItem.item_id).filter(LearningItem.container_id == goal.reference_id)
                 else:
                    query = query.filter(QuizProgress.user_id == goal.user_id)
                 
                 # Period check is hard for `times_correct` as it's a counter.
                 # We can only return TOTAL correct.
                 return query.scalar() or 0

        # Fallback to legacy logic
        if goal.goal_type == 'flashcards_reviewed':
            if goal.period == 'daily': return metrics['flashcard_reviews_today']
            if goal.period == 'weekly': return metrics['flashcard_reviews_week']
            return metrics['flashcard_summary']['mastered']
        if goal.goal_type == 'quizzes_practiced':
             if goal.period == 'daily': return metrics['quiz_attempts_today']
             if goal.period == 'weekly': return metrics['quiz_attempts_week']
             return metrics['quiz_summary']['mastered']
             
        return 0

    progress: list[dict[str, object]] = []

    # Fetch all referenced containers in one batch for efficiency
    reference_ids = {goal.reference_id for goal in goals if goal.scope == 'container' and goal.reference_id}
    containers = {}
    if reference_ids:
        from ...models import LearningContainer
        found_containers = LearningContainer.query.filter(LearningContainer.container_id.in_(reference_ids)).all()
        containers = {c.container_id: c.title for c in found_containers}

    today = datetime.now(timezone.utc).date()
    
    history_updates_pending = False

    for goal in goals:
        # Determine display props properties based on domain/metric
        config = GOAL_TYPE_CONFIG.get(goal.goal_type)
        if not config:
            # Generate default config display
            config = {
                'label': goal.title or 'Mục tiêu',
                'description': goal.description or '',
                'unit': 'điểm' if goal.metric == 'points' else 'lượt',
                'icon': 'star',
                'endpoint': 'main.dashboard'
            }
            if goal.domain == 'flashcard': 
                config['icon'] = 'clone'
                config['endpoint'] = 'learning.flashcard.dashboard'
            elif goal.domain == 'quiz': 
                config['icon'] = 'circle-question'
                config['endpoint'] = 'learning.quiz_learning.quiz_learning_dashboard'

        current_value = _get_metric_value(goal)
        percent = 0
        if goal.target_value:
            percent = min(100, round((current_value / goal.target_value) * 100)) if goal.target_value else 0
        
        container_title = None
        if goal.scope == 'container' and goal.reference_id:
            container_title = containers.get(goal.reference_id)
            
        display_scope = 'Toàn hệ thống'
        if goal.scope == 'container':
             display_scope = container_title if container_title else 'Bộ cụ thể'

        # Calculate Statistics
        days_since_start = 0
        # days_missed = 0 # (Removed unused variable)
        if goal.start_date:
            delta = today - goal.start_date
            days_since_start = max(0, delta.days)
        
        # Metric human label
        metric_label = 'Tiêu chí'
        if goal.metric == 'items_reviewed': metric_label = 'Thẻ đã ôn'
        elif goal.metric == 'new_items': metric_label = 'Thẻ mới học'
        elif goal.metric == 'mastered': metric_label = 'Thẻ thuộc bài'
        elif goal.metric == 'items_answered': metric_label = 'Câu hỏi đã làm'
        elif goal.metric == 'items_correct': metric_label = 'Câu đúng'
        elif goal.metric == 'points': metric_label = 'Điểm số (XP)'

        # --- History Tracking Logic ---
        is_today_met = percent >= 100
        
        # Upsert Today's History
        todays_log = GoalDailyHistory.query.filter_by(goal_id=goal.goal_id, date=today).first()
        if not todays_log:
            todays_log = GoalDailyHistory(
                goal_id=goal.goal_id,
                date=today,
                current_value=current_value,
                target_value=goal.target_value,
                is_met=is_today_met
            )
            db.session.add(todays_log)
            history_updates_pending = True
        else:
            # Only update if changed to avoid unnecessary heavy DB usage if possible, 
            # though SQLAlchemy handles dirty checks.
            if todays_log.current_value != current_value or todays_log.is_met != is_today_met:
                todays_log.current_value = current_value
                todays_log.is_met = is_today_met
                todays_log.target_value = goal.target_value
                history_updates_pending = True

        # Fetch Last 6 Days for Chart
        start_history = today - timedelta(days=6)
        past_logs = GoalDailyHistory.query.filter(
            GoalDailyHistory.goal_id == goal.goal_id,
            GoalDailyHistory.date >= start_history,
            GoalDailyHistory.date < today
        ).all()
        
        log_map = {l.date: l.is_met for l in past_logs}
        history_7_days = []
        for i in range(6, -1, -1): # [6, 5, 4, 3, 2, 1, 0]
            d = today - timedelta(days=i)
            if i == 0: # Today
                history_7_days.append(is_today_met)
            else:
                history_7_days.append(log_map.get(d, False))

        progress.append(
            {
                'id': goal.goal_id,
                'title': goal.title or config['label'],
                'description': goal.description or config['description'],
                'period_label': PERIOD_LABELS.get(goal.period, goal.period),
                'current_value': current_value,
                'target_value': goal.target_value,
                'unit': config['unit'],
                'percent': percent,
                'url': url_for(config['endpoint']),
                'icon': config['icon'],
                'start_date': goal.start_date,
                'due_date': goal.due_date,
                'notes': goal.notes,
                'is_active': goal.is_active,
                'domain': goal.domain, 
                'scope': goal.scope,
                'display_scope': display_scope,
                'is_completed': is_today_met,
                'history_7_days': history_7_days, # New Field
                # New Stats
                'days_since_start': days_since_start,
                'metric_label': metric_label,
                'reference_id': goal.reference_id,
                'container_url': url_for('learning.flashcard.dashboard', preSelect=goal.reference_id) if goal.domain == 'flashcard' and goal.scope == 'container' and goal.reference_id else (
                                 url_for('learning.quiz_learning.quiz_learning_dashboard', preSelect=goal.reference_id) if goal.domain == 'quiz' and goal.scope == 'container' and goal.reference_id else None
                )
            }
        )

    if history_updates_pending:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            # Do not raise, as display is more important than history log in this context
    
    return progress

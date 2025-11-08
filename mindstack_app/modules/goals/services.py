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

    def _goal_value(goal: LearningGoal) -> int:
        if goal.goal_type == 'flashcards_reviewed':
            if goal.period == 'daily':
                return metrics['flashcard_reviews_today']
            if goal.period == 'weekly':
                return metrics['flashcard_reviews_week']
            return metrics['flashcard_summary']['mastered']
        if goal.goal_type == 'quizzes_practiced':
            if goal.period == 'daily':
                return metrics['quiz_attempts_today']
            if goal.period == 'weekly':
                return metrics['quiz_attempts_week']
            return metrics['quiz_summary']['mastered']
        if goal.goal_type == 'lessons_completed':
            if goal.period == 'daily':
                return metrics['course_updates_today']
            if goal.period == 'weekly':
                return metrics['course_updates_week']
            return metrics['course_summary']['completed']
        return 0

    progress: list[dict[str, object]] = []

    for goal in goals:
        config = GOAL_TYPE_CONFIG.get(goal.goal_type)
        if not config:
            continue
        current_value = _goal_value(goal)
        percent = 0
        if goal.target_value:
            percent = min(100, round((current_value / goal.target_value) * 100)) if goal.target_value else 0
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
            }
        )

    return progress

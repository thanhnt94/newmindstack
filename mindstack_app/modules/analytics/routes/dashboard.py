from flask import render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta, date

from mindstack_app.models import db, ScoreLog, LearningProgress, LearningContainer, LearningItem
from .. import analytics_bp
from ..services.metrics import (
    get_leaderboard_data,
    compute_learning_streaks,
    get_user_container_options,
    ITEM_TYPE_LABELS
)

@analytics_bp.route('/')
@login_required
def dashboard():
    """
    Route chính để hiển thị trang dashboard thống kê.
    """
    initial_sort_by = request.args.get('sort_by', 'total_score')
    initial_timeframe = request.args.get('timeframe', 'all_time')
    leaderboard_data = get_leaderboard_data(initial_sort_by, initial_timeframe, viewer=current_user)
    
    score_summary = (
        db.session.query(
            func.sum(ScoreLog.score_change).label('total_score'),
            func.count(func.distinct(func.date(ScoreLog.timestamp))).label('active_days'),
            func.max(ScoreLog.timestamp).label('last_activity'),
            func.count(ScoreLog.log_id).label('entry_count'),
        )
        .filter(ScoreLog.user_id == current_user.user_id)
        .one()
    )

    total_score_all_time = int(score_summary.total_score or 0)
    active_days = int(score_summary.active_days or 0)
    last_activity_value = score_summary.last_activity.isoformat() if score_summary.last_activity else None
    total_entries = int(score_summary.entry_count or 0)
    average_daily_score = round(total_score_all_time / active_days, 1) if active_days else 0

    last_30_start = date.today() - timedelta(days=29)
    last_30_score = (
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(
            ScoreLog.user_id == current_user.user_id,
            ScoreLog.timestamp >= datetime.combine(last_30_start, datetime.min.time()),
        )
        .scalar()
        or 0
    )
    average_recent_score = round(last_30_score / 30, 1) if last_30_score else 0

    current_streak, longest_streak = compute_learning_streaks(current_user.user_id)

    flashcard_score_total = int(
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(
            ScoreLog.user_id == current_user.user_id,
            ScoreLog.item_type == 'FLASHCARD',
        )
        .scalar()
        or 0
    )
    flashcard_summary = (
        db.session.query(
            func.sum(LearningProgress.times_correct).label('correct'),
            func.sum(LearningProgress.times_incorrect).label('incorrect'),
            func.sum(LearningProgress.times_vague).label('vague'),
            func.avg(LearningProgress.correct_streak).label('avg_streak'),
            func.max(LearningProgress.correct_streak).label('best_streak'),
        )
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
        .one()
    )
    flashcard_correct_total = int(flashcard_summary.correct or 0)
    flashcard_incorrect_total = int(flashcard_summary.incorrect or 0)
    flashcard_vague_total = int(flashcard_summary.vague or 0)
    flashcard_attempt_total = flashcard_correct_total + flashcard_incorrect_total + flashcard_vague_total
    flashcard_accuracy_percent = (
        round((flashcard_correct_total / flashcard_attempt_total) * 100, 1)
        if flashcard_attempt_total
        else None
    )
    flashcard_avg_streak = float(flashcard_summary.avg_streak or 0) if flashcard_summary.avg_streak is not None else 0.0
    flashcard_best_streak = int(flashcard_summary.best_streak or 0) if flashcard_summary.best_streak is not None else 0
    flashcard_mastered_count = LearningProgress.query.filter_by(
        user_id=current_user.user_id, 
        learning_mode=LearningProgress.MODE_FLASHCARD,
        status='mastered'
    ).count()
    flashcard_total_cards = LearningProgress.query.filter_by(
        user_id=current_user.user_id,
        learning_mode=LearningProgress.MODE_FLASHCARD
    ).count()
    flashcard_sets_count = (
        db.session.query(func.count(func.distinct(LearningContainer.container_id)))
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningContainer.container_type == 'FLASHCARD_SET',
            LearningItem.item_type == 'FLASHCARD',
        )
        .scalar()
        or 0
    )

    quiz_score_total = int(
        db.session.query(func.sum(ScoreLog.score_change))
        .filter(
            ScoreLog.user_id == current_user.user_id,
            ScoreLog.item_type == 'QUIZ_MCQ',
        )
        .scalar()
        or 0
    )
    quiz_summary = (
        db.session.query(
            func.sum(LearningProgress.times_correct).label('correct'),
            func.sum(LearningProgress.times_incorrect).label('incorrect'),
            func.avg(LearningProgress.correct_streak).label('avg_streak'),
            func.max(LearningProgress.correct_streak).label('best_streak'),
        )
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ
        )
        .one()
    )
    quiz_correct_total = int(quiz_summary.correct or 0)
    quiz_incorrect_total = int(quiz_summary.incorrect or 0)
    quiz_attempt_total = quiz_correct_total + quiz_incorrect_total
    quiz_accuracy_percent = (
        round((quiz_correct_total / quiz_attempt_total) * 100, 1)
        if quiz_attempt_total
        else None
    )
    quiz_avg_streak = float(quiz_summary.avg_streak or 0) if quiz_summary.avg_streak is not None else 0.0
    quiz_best_streak = int(quiz_summary.best_streak or 0) if quiz_summary.best_streak is not None else 0
    quiz_questions_answered = LearningProgress.query.filter_by(
        user_id=current_user.user_id,
        learning_mode=LearningProgress.MODE_QUIZ
    ).count()
    quiz_mastered_count = LearningProgress.query.filter_by(
        user_id=current_user.user_id, 
        learning_mode=LearningProgress.MODE_QUIZ,
        status='mastered'
    ).count()
    quiz_sets_started_count = (
        db.session.query(func.count(func.distinct(LearningContainer.container_id)))
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ,
            LearningContainer.container_type == 'QUIZ_SET',
            LearningItem.item_type == 'QUIZ_MCQ',
        )
        .scalar()
        or 0
    )

    courses_started_count = (
        db.session.query(func.count(func.distinct(LearningContainer.container_id)))
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
            LearningContainer.container_type == 'COURSE',
            LearningItem.item_type == 'LESSON',
        )
        .scalar()
        or 0
    )
    lessons_completed_count = LearningProgress.query.filter(
        LearningProgress.user_id == current_user.user_id,
        LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
        LearningProgress.mastery >= 1.0
    ).count()
    courses_in_progress_count = LearningProgress.query.filter(
        LearningProgress.user_id == current_user.user_id,
        LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
        LearningProgress.mastery > 0.0,
        LearningProgress.mastery < 1.0,
    ).count()
    course_summary = (
        db.session.query(
            func.avg(LearningProgress.mastery * 100).label('avg_completion'),
            func.max(LearningProgress.last_reviewed).label('last_progress'),
        )
        .filter(
            LearningProgress.user_id == current_user.user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE
        )
        .one()
    )
    course_avg_completion = float(course_summary.avg_completion or 0)
    course_last_progress = course_summary.last_progress.isoformat() if course_summary.last_progress else None

    dashboard_data = {
        'flashcard_score': flashcard_score_total,
        'learned_distinct_overall': flashcard_total_cards,
        'learned_sets_count': flashcard_sets_count,
        'flashcard_accuracy_percent': flashcard_accuracy_percent,
        'flashcard_attempt_total': flashcard_attempt_total,
        'flashcard_correct_total': flashcard_correct_total,
        'flashcard_incorrect_total': flashcard_incorrect_total,
        'flashcard_mastered_count': flashcard_mastered_count,
        'flashcard_avg_streak_overall': round(flashcard_avg_streak, 1) if flashcard_avg_streak else 0.0,
        'flashcard_best_streak_overall': flashcard_best_streak,
        'quiz_score': quiz_score_total,
        'questions_answered_count': quiz_questions_answered,
        'quiz_sets_started_count': quiz_sets_started_count,
        'quiz_accuracy_percent': quiz_accuracy_percent,
        'quiz_attempt_total': quiz_attempt_total,
        'quiz_correct_total': quiz_correct_total,
        'quiz_incorrect_total': quiz_incorrect_total,
        'quiz_mastered_count': quiz_mastered_count,
        'quiz_avg_streak_overall': round(quiz_avg_streak, 1) if quiz_avg_streak else 0.0,
        'quiz_best_streak_overall': quiz_best_streak,
        'courses_started_count': courses_started_count,
        'lessons_completed_count': lessons_completed_count,
        'courses_in_progress_count': courses_in_progress_count,
        'course_avg_completion_percent': round(course_avg_completion, 1) if course_avg_completion else 0.0,
        'course_last_progress': course_last_progress,
        'total_score_all_time': total_score_all_time,
        'total_activity_entries': total_entries,
        'active_days': active_days,
        'average_daily_score': average_daily_score,
        'total_score_last_30_days': int(last_30_score),
        'average_daily_score_recent': average_recent_score,
        'last_activity': last_activity_value,
        'current_learning_streak': current_streak,
        'longest_learning_streak': longest_streak,
    }

    recent_logs = (
        ScoreLog.query.filter_by(user_id=current_user.user_id)
        .order_by(ScoreLog.timestamp.desc())
        .limit(6)
        .all()
    )
    recent_activity = [
        {
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'score_change': int(log.score_change or 0),
            'reason': log.reason or 'Hoạt động học tập',
            'item_type': log.item_type or 'OTHER',
            'item_type_label': ITEM_TYPE_LABELS.get(log.item_type or '', 'Hoạt động khác'),
        }
        for log in recent_logs
    ]

    flashcard_sets = get_user_container_options(
        current_user.user_id,
        'FLASHCARD_SET',
        LearningProgress.MODE_FLASHCARD,
        'last_reviewed',
        item_type='FLASHCARD',
    )
    quiz_sets = get_user_container_options(
        current_user.user_id,
        'QUIZ_SET',
        LearningProgress.MODE_QUIZ,
        'last_reviewed',
        item_type='QUIZ_MCQ',
    )
    course_sets = get_user_container_options(
        current_user.user_id,
        'COURSE',
        LearningProgress.MODE_COURSE,
        'last_reviewed',
        item_type='LESSON',
    )

    return render_template(
        'v3/pages/analytics/dashboard.html',
        leaderboard_data=leaderboard_data,
        dashboard_data=dashboard_data,
        current_sort_by=initial_sort_by,
        current_timeframe=initial_timeframe,
        flashcard_sets=flashcard_sets,
        quiz_sets=quiz_sets,
        course_sets=course_sets,
        recent_activity=recent_activity,
    )

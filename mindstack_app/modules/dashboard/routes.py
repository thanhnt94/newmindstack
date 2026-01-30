# File: mindstack_app/modules/dashboard/routes.py
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.core.extensions import db
from mindstack_app.models import UserGoal, User
from mindstack_app.modules.goals.view_helpers import build_goal_progress
from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
from . import blueprint as dashboard_bp

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Trang dashboard tổng quan của người dùng."""
    user_id = current_user.user_id
    
    # 1. Fetch Summaries using LearningMetricsService
    flashcard_summary = LearningMetricsService.get_user_learning_summary(user_id)['flashcard']
    quiz_summary = LearningMetricsService.get_user_learning_summary(user_id)['quiz']
    course_summary = LearningMetricsService.get_user_learning_summary(user_id)['course']
    
    # 2. Daily/Weekly activity counts
    flashcard_reviews_today = LearningMetricsService.get_todays_activity_counts(user_id)['flashcard']
    flashcard_reviews_week = LearningMetricsService.get_week_activity_counts(user_id)['flashcard']
    quiz_attempts_today = LearningMetricsService.get_todays_activity_counts(user_id)['quiz']
    quiz_attempts_week = LearningMetricsService.get_week_activity_counts(user_id)['quiz']
    course_updates_today = LearningMetricsService.get_todays_activity_counts(user_id)['course']
    course_updates_week = LearningMetricsService.get_week_activity_counts(user_id)['course']
    
    # 3. Scores & Streaks
    score_data = LearningMetricsService.get_score_breakdown(user_id)
    score_today = score_data['today']
    score_week = score_data['week']
    score_total = score_data['total']
    weekly_active_days = LearningMetricsService.get_weekly_active_days_count(user_id)
    
    score_overview = {
        'today': score_today,
        'week': score_week,
        'total': score_total,
        'active_days': weekly_active_days
    }

    # 4. Motivation message
    activity_parts = []
    if flashcard_reviews_today > 0: activity_parts.append(f"ôn {flashcard_reviews_today} thẻ")
    if quiz_attempts_today > 0: activity_parts.append(f"làm {quiz_attempts_today} câu quiz")
    
    if activity_parts:
        if len(activity_parts) == 1:
            motivation_message = f"Hôm nay bạn đã {activity_parts[0]}."
        else:
            motivation_message = f"Hôm nay bạn đã {', '.join(activity_parts[:-1])} và {activity_parts[-1]}."
        if score_today > 0:
            motivation_message += f" Bạn còn kiếm thêm {score_today} điểm thưởng nữa!"
    else:
        motivation_message = "Hôm nay bạn chưa bắt đầu phiên học nào. Chọn một hoạt động bên dưới để khởi động nhé!"

    # 5. Shortcut Actions (Corrected Endpoints)
    shortcut_actions = []
    if flashcard_summary['due'] > 0:
        shortcut_actions.append({
            'title': 'Ôn flashcard đến hạn',
            'description': f"{flashcard_summary['due']} thẻ đang chờ bạn.",
            'icon': 'bolt',
            'url': url_for('flashcard.flashcard_dashboard_internal.dashboard'),
        })
    if quiz_summary['learning'] > 0:
        shortcut_actions.append({
            'title': 'Tiếp tục luyện quiz',
            'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
            'icon': 'circle-question',
            'url': url_for('quiz.quiz_learning.dashboard'),
        })
    if course_summary['in_progress_lessons'] > 0:
        shortcut_actions.append({
            'title': 'Hoàn thiện khóa học',
            'description': f"{course_summary['in_progress_lessons']} bài học đang dang dở.",
            'icon': 'graduation-cap',
            'url': url_for('course.course_learning_dashboard'),
        })

    if not shortcut_actions:
        shortcut_actions.append({
            'title': 'Khởi động với Flashcard',
            'description': 'Tạo đà học tập với vài thẻ đầu tiên.',
            'icon': 'sparkles',
            'url': url_for('flashcard.flashcard_dashboard_internal.dashboard'),
        })

    # 6. Goals
    goals = UserGoal.query.filter_by(user_id=user_id, is_active=True).order_by(UserGoal.created_at.desc()).all()
    
    goal_progress = build_goal_progress(goals) 

    return render_dynamic_template('pages/dashboard/index.html',
        flashcard_summary=flashcard_summary,
        quiz_summary=quiz_summary,
        course_summary=course_summary,
        score_overview=score_overview,
        motivation_message=motivation_message,
        shortcut_actions=shortcut_actions,
        goal_progress=goal_progress
    )

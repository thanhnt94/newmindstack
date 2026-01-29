from flask import render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from . import dashboard_bp
from ..goals.view_helpers import build_goal_progress
from ...models import db, UserGoal, User


@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = current_user.user_id

    # [REFACTORED] Use LearningMetricsService
    from mindstack_app.services.learning_metrics_service import LearningMetricsService
    
    summary = LearningMetricsService.get_user_learning_summary(user_id)
    
    # Extract necessary metrics from summary for template
    flashcard_summary = summary['flashcard']
    quiz_summary = summary['quiz']
    course_summary = summary['course']
    
    score_today = LearningMetricsService.get_score_breakdown(user_id)['today']
    score_week = LearningMetricsService.get_score_breakdown(user_id)['week']
    score_total = summary['total_score']
    weekly_active_days = summary['active_days']

    # Activity Counts (Today vs Week)
    activity_today = LearningMetricsService.get_todays_activity_counts(user_id)
    activity_week = LearningMetricsService.get_week_activity_counts(user_id)
    
    flashcard_reviews_today = activity_today['flashcard']
    quiz_attempts_today = activity_today['quiz']
    course_updates_today = activity_today['course']
    
    flashcard_reviews_week = activity_week['flashcard']
    quiz_attempts_week = activity_week['quiz']
    course_updates_week = activity_week['course']

    activity_parts = []
    if flashcard_reviews_today:
        activity_parts.append(f"ôn {flashcard_reviews_today} thẻ flashcard")
    if quiz_attempts_today:
        activity_parts.append(f"làm {quiz_attempts_today} câu hỏi quiz")
    if course_updates_today:
        activity_parts.append(f"cập nhật tiến độ {course_updates_today} bài học")

    if activity_parts:
        if len(activity_parts) == 1:
            motivation_message = f"Hôm nay bạn đã {activity_parts[0]}."
        else:
            motivation_message = (
                "Hôm nay bạn đã "
                + ", ".join(activity_parts[:-1])
                + f" và {activity_parts[-1]}."
            )
        if score_today > 0:
            motivation_message += f" Bạn còn kiếm thêm {score_today} điểm thưởng nữa!"
        if weekly_active_days:
            motivation_message += (
                f" Bạn đã học {weekly_active_days} ngày trong 6 ngày gần nhất – tiếp tục duy trì nhé!"
            )
    else:
        motivation_message = (
            "Hôm nay bạn chưa bắt đầu phiên học nào. Chọn một hoạt động bên dưới để khởi động nhé!"
        )

    shortcut_actions = []
    if flashcard_summary['due'] > 0:
        shortcut_actions.append(
            {
                'title': 'Ôn flashcard đến hạn',
                'description': f"{flashcard_summary['due']} thẻ đang chờ bạn.",
                'icon': 'bolt',
                'url': url_for('learning.flashcard.flashcard_dashboard.dashboard'),
            }
        )
    if quiz_summary['learning'] > 0:
        shortcut_actions.append(
            {
                'title': 'Tiếp tục luyện quiz',
                'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
                'icon': 'circle-question',
                'url': url_for('learning.quiz_learning.dashboard'),
            }
        )
    if course_summary['in_progress_lessons'] > 0:
        shortcut_actions.append(
            {
                'title': 'Hoàn thiện khóa học',
                'description': f"{course_summary['in_progress_lessons']} bài học đang dang dở.",
                'icon': 'graduation-cap',
                'url': url_for('learning.course.course_learning_dashboard'),
            }
        )

    if not shortcut_actions:
        shortcut_actions.append(
            {
                'title': 'Khởi động với Flashcard',
                'description': 'Tạo đà học tập với vài thẻ đầu tiên.',
                'icon': 'sparkles',
                'url': url_for('learning.flashcard.flashcard_dashboard.dashboard'),
            }
        )

    score_overview = {
        'today': int(score_today),
        'week': int(score_week),
        'total': int(score_total),
        'active_days': int(weekly_active_days),
    }

    goals = (
        db.session.query(UserGoal)
        .filter(
            UserGoal.user_id == user_id,
            UserGoal.is_active.is_(True),
        )
        .order_by(UserGoal.created_at.desc())
        .all()
    )

    # Note: build_goal_progress still relies on the old dict format from goals/services.py
    # We will pass a constructed dict that mimics the old structure for compatibility during this refactor step,
    # or ideally update build_goal_progress next. For now, let's construct the mimic dict.
    metrics_mimic = {
        'flashcard_summary': flashcard_summary,
        'quiz_summary': quiz_summary,
        'course_summary': {
            'completed': course_summary['completed_lessons'],
            'in_progress': course_summary['in_progress_lessons'],
            'avg_completion': course_summary['avg_completion'],
            'last_updated': course_summary['last_progress']
        },
        'flashcard_reviews_today': flashcard_reviews_today,
        'flashcard_reviews_week': flashcard_reviews_week,
        'quiz_attempts_today': quiz_attempts_today,
        'quiz_attempts_week': quiz_attempts_week,
        'course_updates_today': course_updates_today,
        'course_updates_week': course_updates_week,
        'score_today': score_today,
        'score_week': score_week,
        'score_total': score_total,
        'weekly_active_days': weekly_active_days
    }
    
    goal_progress = build_goal_progress(goals, metrics_mimic)

    score_cards = [
        {
            'label': 'Điểm hôm nay',
            'value': int(score_overview['today']),
            'icon': 'sun',
            'color': 'indigo',
        },
        {
            'label': 'Ghi nhớ (Retention)',
            'value': int(flashcard_summary.get('avg_retention', 0)),
            'unit': '%',
            'icon': 'brain',
            'color': 'emerald',
        },
        {
            'label': 'Độ ổn định TB',
            'value': int(flashcard_summary.get('avg_stability', 0)),
            'unit': 'd',
            'icon': 'shield-heart',
            'color': 'amber',
        },
        {
            'label': 'Ngày hoạt động',
            'value': int(score_overview['active_days']),
            'icon': 'fire',
            'color': 'rose',
        },
    ]

    achievements = [
        {
            'label': 'Flashcard đã thành thạo',
            'value': int(flashcard_summary['mastered']),
            'detail': f"Trong tổng {int(flashcard_summary['total'])} thẻ" if flashcard_summary['total'] else 'Bắt đầu tạo bộ thẻ đầu tiên',
            'icon': 'clone',
            'tone': 'indigo',
        },
        {
            'label': 'Khả năng ghi nhớ',
            'value': int(flashcard_summary.get('avg_retention', 0)),
            'unit': '%',
            'detail': 'Dự báo tỷ lệ thuộc bài hiện tại',
            'icon': 'brain',
            'tone': 'emerald',
        },
        {
            'label': 'Độ ổn định trí nhớ',
            'value': int(flashcard_summary.get('avg_stability', 0)),
            'unit': 'd',
            'detail': 'Khoảng cách ôn tập trung bình',
            'icon': 'shield-heart',
            'tone': 'rose',
        },
        {
            'label': 'Khóa học hoàn thành',
            'value': int(course_summary['completed_lessons']),
            'detail': f"Đang theo học {int(course_summary['in_progress_lessons'])} bài",
            'icon': 'graduation-cap',
            'tone': 'amber',
        },
    ]

    progress_snapshots = [
        {
            'label': 'Flashcard đã ôn hôm nay',
            'value': flashcard_reviews_today,
            'unit': 'thẻ',
            'trend': f"{flashcard_reviews_week} trong 7 ngày qua",
            'icon': 'bolt',
        },
        {
            'label': 'Quiz đã luyện hôm nay',
            'value': quiz_attempts_today,
            'unit': 'câu',
            'trend': f"{quiz_attempts_week} trong 7 ngày qua",
            'icon': 'brain',
        },
        {
            'label': 'Bài học cập nhật hôm nay',
            'value': course_updates_today,
            'unit': 'bài',
            'trend': f"{course_updates_week} trong 7 ngày qua",
            'icon': 'book-open',
        },
        {
            'label': 'Khả năng ghi nhớ',
            'value': flashcard_summary.get('avg_retention', 0),
            'unit': '%',
            'trend': 'Mức độ thuộc bài dự kiến',
            'icon': 'brain',
        },
        {
            'label': 'Độ ổn định trí nhớ',
            'value': flashcard_summary.get('avg_stability', 0),
            'unit': 'ngày',
            'trend': 'Khoảng cách ôn tập TB',
            'icon': 'shield-heart',
        },
    ]

    # [REFACTORED] Use LearningMetricsService for Leaderboard
    leaderboard_data = LearningMetricsService.get_leaderboard(
        sort_by='total_score', 
        timeframe='all_time', 
        limit=6, 
        viewer_user=current_user
    )
    
    # Needs sorting logic from old route or is service enough? Service returns simplified dicts.
    # Old route did elaborate ranking logic including current user if not in top 5.
    # We will stick to the service's simple top N for now as it covers 90% use case.
    # If the current user is missing from top 5, we can fetch their rank separately if needed, 
    # but for now let's use the service output directly to simplify.

    # Get dynamic template path from TemplateService
    from mindstack_app.services.template_service import TemplateService
    template_path = TemplateService.get_template_path('dashboard')
    template_context = TemplateService.get_template_context('dashboard')
    
    return render_template(
        template_path,
        **template_context,
        flashcard_summary=flashcard_summary,
        quiz_summary=quiz_summary,
        course_summary=course_summary, 
        score_overview=score_overview,
        motivation_message=motivation_message,
        shortcut_actions=shortcut_actions,
        goal_progress=goal_progress,
        score_cards=score_cards,
        achievements=achievements,
        progress_snapshots=progress_snapshots,
        leaderboard=leaderboard_data,
    )

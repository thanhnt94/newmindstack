from flask import render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from . import dashboard_bp
from ..goals.services import build_goal_progress, get_learning_activity
from ...models import db, LearningGoal, User

@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = current_user.user_id

    metrics = get_learning_activity(user_id)

    flashcard_summary = metrics['flashcard_summary']
    quiz_summary = metrics['quiz_summary']
    course_summary = metrics['course_summary']
    flashcard_reviews_today = metrics['flashcard_reviews_today']
    quiz_attempts_today = metrics['quiz_attempts_today']
    course_updates_today = metrics['course_updates_today']
    flashcard_reviews_week = metrics['flashcard_reviews_week']
    quiz_attempts_week = metrics['quiz_attempts_week']
    course_updates_week = metrics['course_updates_week']
    score_today = metrics['score_today']
    score_week = metrics['score_week']
    score_total = metrics['score_total']
    weekly_active_days = metrics['weekly_active_days']

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
                f" Bạn đã học {weekly_active_days} ngày trong 7 ngày gần nhất – tiếp tục duy trì nhé!"
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
                'url': url_for('learning.flashcard.dashboard'),
            }
        )
    if quiz_summary['learning'] > 0:
        shortcut_actions.append(
            {
                'title': 'Tiếp tục luyện quiz',
                'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
                'icon': 'circle-question',
                'url': url_for('learning.quiz_learning.quiz_learning_dashboard'),
            }
        )
    if course_summary['in_progress'] > 0:
        shortcut_actions.append(
            {
                'title': 'Hoàn thiện khóa học',
                'description': f"{course_summary['in_progress']} bài học đang dang dở.",
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
                'url': url_for('learning.flashcard.dashboard'),
            }
        )

    score_overview = {
        'today': int(score_today),
        'week': int(score_week),
        'total': int(score_total),
        'active_days': int(weekly_active_days),
    }

    goals = (
        db.session.query(LearningGoal)
        .filter(
            LearningGoal.user_id == user_id,
            LearningGoal.is_active.is_(True),
        )
        .order_by(LearningGoal.created_at.desc())
        .all()
    )

    goal_progress = build_goal_progress(goals, metrics)

    score_cards = [
        {
            'label': 'Điểm hôm nay',
            'value': score_overview['today'],
            'icon': 'sun',
            'accent': 'from-indigo-500 to-indigo-600',
        },
        {
            'label': 'Điểm 7 ngày',
            'value': score_overview['week'],
            'icon': 'calendar-week',
            'accent': 'from-emerald-500 to-emerald-600',
        },
        {
            'label': 'Điểm tích lũy',
            'value': score_overview['total'],
            'icon': 'trophy',
            'accent': 'from-amber-500 to-amber-600',
        },
        {
            'label': 'Ngày hoạt động',
            'value': score_overview['active_days'],
            'icon': 'fire',
            'accent': 'from-rose-500 to-rose-600',
        },
    ]

    achievements = [
        {
            'label': 'Flashcard đã thành thạo',
            'value': flashcard_summary['mastered'],
            'detail': f"Trong tổng {flashcard_summary['total']} thẻ" if flashcard_summary['total'] else 'Bắt đầu tạo bộ thẻ đầu tiên',
            'icon': 'clone',
            'tone': 'indigo',
        },
        {
            'label': 'Quiz đã nắm vững',
            'value': quiz_summary['mastered'],
            'detail': f"{quiz_summary['completion_percent']}% câu hỏi đã thành thạo",
            'icon': 'circle-question',
            'tone': 'emerald',
        },
        {
            'label': 'Khóa học hoàn thành',
            'value': course_summary['completed'],
            'detail': f"Đang theo học {course_summary['in_progress']} khóa",
            'icon': 'graduation-cap',
            'tone': 'amber',
        },
        {
            'label': 'Điểm thưởng tích lũy',
            'value': score_overview['total'],
            'detail': 'Tích lũy từ mọi hoạt động học tập',
            'icon': 'star',
            'tone': 'violet',
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
    ]

    leaderboard_rows = (
        db.session.query(User.user_id, User.username, User.total_score)
        .order_by(User.total_score.desc())
        .limit(5)
        .all()
    )

    leaderboard = []
    seen_user_ids = set()
    for index, row in enumerate(leaderboard_rows, start=1):
        score_value = int(row.total_score or 0)
        is_current = row.user_id == current_user.user_id
        leaderboard.append(
            {
                'rank': index,
                'username': row.username,
                'score': score_value,
                'is_current_user': is_current,
            }
        )
        seen_user_ids.add(row.user_id)

    if current_user.user_id not in seen_user_ids:
        higher_score_count = (
            db.session.query(func.count(User.user_id))
            .filter(User.total_score > (current_user.total_score or 0))
            .scalar()
            or 0
        )
        leaderboard.append(
            {
                'rank': higher_score_count + 1,
                'username': current_user.username,
                'score': int(current_user.total_score or 0),
                'is_current_user': True,
            }
        )
        leaderboard.sort(key=lambda item: item['rank'])

    return render_template(
        'dashboard/index.html',
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
        leaderboard=leaderboard,
    )

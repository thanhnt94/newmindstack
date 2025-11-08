# Tệp: web/mindstack_app/modules/main/routes.py
# Version: 1.1
# Mục đích: Định nghĩa Blueprint và import các routes liên quan.
# ĐÃ SỬA: Thay đổi logic route '/' để hiển thị trang giới thiệu thay vì redirect thẳng đến trang login.

from datetime import datetime, timedelta, timezone

from flask import flash, redirect, render_template, url_for
from flask_login import login_required, current_user
from sqlalchemy import case, func, distinct

from . import main_bp
from ...models import (
    db,
    FlashcardProgress,
    QuizProgress,
    CourseProgress,
    ScoreLog,
    LearningGoal,
    User,
)
from .forms import GoalForm


GOAL_TYPE_CONFIG = {
    'flashcards_reviewed': {
        'label': 'Flashcard',
        'description': 'Ôn luyện flashcard và giữ chuỗi học.',
        'unit': 'thẻ',
        'icon': 'clone',
        'endpoint': 'learning.flashcard_learning.flashcard_learning_dashboard',
    },
    'quizzes_practiced': {
        'label': 'Quiz',
        'description': 'Luyện quiz để củng cố kiến thức.',
        'unit': 'câu',
        'icon': 'circle-question',
        'endpoint': 'learning.quiz_learning.quiz_learning_dashboard',
    },
    'lessons_completed': {
        'label': 'Bài học',
        'description': 'Hoàn thành các bài học trong khóa.',
        'unit': 'bài',
        'icon': 'graduation-cap',
        'endpoint': 'learning.course_learning.course_learning_dashboard',
    },
}

PERIOD_LABELS = {
    'daily': 'Hôm nay',
    'weekly': '7 ngày qua',
    'total': 'Tổng cộng',
}


@main_bp.route('/')
def index():
    """
    Mô tả: Trang chủ của ứng dụng.
    Nếu người dùng đã đăng nhập, chuyển hướng đến dashboard.
    Nếu chưa, hiển thị trang giới thiệu.
    """
    if current_user.is_authenticated:
        # Nếu đã đăng nhập, vào dashboard
        return redirect(url_for('main.dashboard'))
    # Nếu chưa đăng nhập, hiển thị trang giới thiệu
    return render_template('main/landing_page.html')


@main_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required  # Yêu cầu người dùng phải đăng nhập để truy cập route này
def dashboard():
    user_id = current_user.user_id

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=6)

    flashcard_row = (
        db.session.query(
            func.count(FlashcardProgress.progress_id).label('total'),
            func.sum(
                case((FlashcardProgress.status == 'mastered', 1), else_=0)
            ).label('mastered'),
            func.sum(
                case((FlashcardProgress.status == 'learning', 1), else_=0)
            ).label('learning'),
            func.sum(case((FlashcardProgress.status == 'new', 1), else_=0)).label('new'),
            func.sum(case((FlashcardProgress.status == 'hard', 1), else_=0)).label('hard'),
            func.sum(
                case((FlashcardProgress.status == 'reviewing', 1), else_=0)
            ).label('reviewing'),
            func.sum(
                case((FlashcardProgress.due_time <= func.now(), 1), else_=0)
            ).label('due'),
        )
        .filter(FlashcardProgress.user_id == user_id)
        .first()
    )

    quiz_row = (
        db.session.query(
            func.count(QuizProgress.progress_id).label('total'),
            func.sum(case((QuizProgress.status == 'mastered', 1), else_=0)).label(
                'mastered'
            ),
            func.sum(case((QuizProgress.status == 'learning', 1), else_=0)).label(
                'learning'
            ),
            func.sum(case((QuizProgress.status == 'new', 1), else_=0)).label('new'),
            func.sum(case((QuizProgress.status == 'hard', 1), else_=0)).label('hard'),
        )
        .filter(QuizProgress.user_id == user_id)
        .first()
    )

    course_row = (
        db.session.query(
            func.count(CourseProgress.progress_id).label('total'),
            func.sum(
                case((CourseProgress.completion_percentage >= 100, 1), else_=0)
            ).label('completed'),
            func.sum(
                case((CourseProgress.completion_percentage < 100, 1), else_=0)
            ).label('in_progress'),
            func.avg(CourseProgress.completion_percentage).label('avg_completion'),
            func.max(CourseProgress.last_updated).label('last_updated'),
        )
        .filter(CourseProgress.user_id == user_id)
        .first()
    )

    def _as_int(value):
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
    flashcard_mastered = flashcard_summary['mastered']
    flashcard_summary['completion_percent'] = (
        round((flashcard_mastered / flashcard_total) * 100)
        if flashcard_total
        else 0
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
                'url': url_for('learning.flashcard_learning.flashcard_learning_dashboard'),
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
                'url': url_for('learning.course_learning.course_learning_dashboard'),
            }
        )

    if not shortcut_actions:
        shortcut_actions.append(
            {
                'title': 'Khởi động với Flashcard',
                'description': 'Tạo đà học tập với vài thẻ đầu tiên.',
                'icon': 'sparkles',
                'url': url_for('learning.flashcard_learning.flashcard_learning_dashboard'),
            }
        )

    score_overview = {
        'today': int(score_today),
        'week': int(score_week),
        'total': int(score_total),
        'active_days': int(weekly_active_days),
    }

    goal_form = GoalForm()
    goal_form.goal_type.choices = [
        (key, config['label']) for key, config in GOAL_TYPE_CONFIG.items()
    ]

    if goal_form.validate_on_submit():
        selected_type = goal_form.goal_type.data
        config = GOAL_TYPE_CONFIG.get(selected_type)
        if config is None:
            flash('Loại mục tiêu không hợp lệ.', 'error')
        else:
            goal = (
                db.session.query(LearningGoal)
                .filter(
                    LearningGoal.user_id == user_id,
                    LearningGoal.goal_type == selected_type,
                    LearningGoal.period == goal_form.period.data,
                    LearningGoal.is_active.is_(True),
                )
                .first()
            )
            if goal:
                goal.target_value = goal_form.target_value.data
                goal.description = goal.description or config['description']
                message = 'Đã cập nhật mục tiêu hiện tại.'
            else:
                goal = LearningGoal(
                    user_id=user_id,
                    goal_type=selected_type,
                    period=goal_form.period.data,
                    target_value=goal_form.target_value.data,
                    description=config['description'],
                )
                db.session.add(goal)
                message = 'Đã tạo mục tiêu mới.'
            db.session.commit()
            flash(message, 'success')
            return redirect(url_for('main.dashboard'))

    goals = (
        db.session.query(LearningGoal)
        .filter(
            LearningGoal.user_id == user_id,
            LearningGoal.is_active.is_(True),
        )
        .order_by(LearningGoal.created_at.desc())
        .all()
    )

    metrics = {
        'flashcard_reviews_today': flashcard_reviews_today,
        'flashcard_reviews_week': flashcard_reviews_week,
        'flashcard_mastered': flashcard_summary['mastered'],
        'quiz_attempts_today': quiz_attempts_today,
        'quiz_attempts_week': quiz_attempts_week,
        'quiz_mastered': quiz_summary['mastered'],
        'course_updates_today': course_updates_today,
        'course_updates_week': course_updates_week,
        'course_completed': course_summary['completed'],
    }

    def _goal_value(goal: LearningGoal) -> int:
        if goal.goal_type == 'flashcards_reviewed':
            if goal.period == 'daily':
                return metrics['flashcard_reviews_today']
            if goal.period == 'weekly':
                return metrics['flashcard_reviews_week']
            return metrics['flashcard_mastered']
        if goal.goal_type == 'quizzes_practiced':
            if goal.period == 'daily':
                return metrics['quiz_attempts_today']
            if goal.period == 'weekly':
                return metrics['quiz_attempts_week']
            return metrics['quiz_mastered']
        if goal.goal_type == 'lessons_completed':
            if goal.period == 'daily':
                return metrics['course_updates_today']
            if goal.period == 'weekly':
                return metrics['course_updates_week']
            return metrics['course_completed']
        return 0

    goal_progress = []
    for goal in goals:
        config = GOAL_TYPE_CONFIG.get(goal.goal_type)
        if not config:
            continue
        current_value = _goal_value(goal)
        percent = 0
        if goal.target_value > 0:
            percent = min(100, round((current_value / goal.target_value) * 100))
        goal_progress.append(
            {
                'id': goal.goal_id,
                'title': config['label'],
                'description': config['description'],
                'period_label': PERIOD_LABELS.get(goal.period, goal.period),
                'current_value': current_value,
                'target_value': goal.target_value,
                'unit': config['unit'],
                'percent': percent,
                'url': url_for(config['endpoint']),
                'icon': config['icon'],
            }
        )

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
        'main/dashboard.html',
        flashcard_summary=flashcard_summary,
        quiz_summary=quiz_summary,
        course_summary=course_summary,
        score_overview=score_overview,
        motivation_message=motivation_message,
        shortcut_actions=shortcut_actions,
        goal_form=goal_form,
        goal_progress=goal_progress,
        score_cards=score_cards,
        achievements=achievements,
        progress_snapshots=progress_snapshots,
        leaderboard=leaderboard,
    )

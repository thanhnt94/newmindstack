# Tệp: web/mindstack_app/modules/main/routes.py
# Version: 1.1
# Mục đích: Định nghĩa Blueprint và import các routes liên quan.
# ĐÃ SỬA: Thay đổi logic route '/' để hiển thị trang giới thiệu thay vì redirect thẳng đến trang login.

from datetime import datetime, timedelta, timezone

from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import case, func, distinct

from . import main_bp
from ...models import (
    db,
    FlashcardProgress,
    QuizProgress,
    CourseProgress,
    ScoreLog,
)


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


@main_bp.route('/dashboard')
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

    recent_actions_rows = (
        db.session.query(ScoreLog)
        .filter(ScoreLog.user_id == user_id)
        .order_by(ScoreLog.timestamp.desc())
        .limit(5)
        .all()
    )

    recent_actions = []
    for row in recent_actions_rows:
        timestamp = row.timestamp
        if timestamp is None:
            timestamp = now
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        score_change = int(row.score_change or 0)
        if score_change > 0:
            score_badge = f"+{score_change} điểm"
            tone = 'positive'
        elif score_change < 0:
            score_badge = f"{score_change} điểm"
            tone = 'negative'
        else:
            score_badge = "0 điểm"
            tone = 'neutral'

        recent_actions.append(
            {
                'title': row.reason or 'Hoạt động học tập',
                'timestamp_display': timestamp.strftime('%H:%M'),
                'date_display': timestamp.strftime('%d/%m'),
                'score_badge': score_badge,
                'tone': tone,
            }
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

    quick_actions = []
    if flashcard_summary['due'] > 0:
        quick_actions.append(
            {
                'title': 'Ôn flashcard đến hạn',
                'description': f"{flashcard_summary['due']} thẻ đang chờ bạn.",
                'icon': 'bolt',
                'url': url_for('learning.flashcard_learning.flashcard_learning_dashboard'),
            }
        )
    if quiz_summary['learning'] > 0:
        quick_actions.append(
            {
                'title': 'Tiếp tục luyện quiz',
                'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
                'icon': 'circle-question',
                'url': url_for('learning.quiz_learning.quiz_learning_dashboard'),
            }
        )
    if course_summary['in_progress'] > 0:
        quick_actions.append(
            {
                'title': 'Hoàn thiện khóa học',
                'description': f"{course_summary['in_progress']} bài học đang dang dở.",
                'icon': 'graduation-cap',
                'url': url_for('learning.course_learning.course_learning_dashboard'),
            }
        )

    if not quick_actions:
        quick_actions.append(
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
    }

    today_activity = {
        'flashcards': flashcard_reviews_today,
        'quizzes': quiz_attempts_today,
        'courses': course_updates_today,
    }

    return render_template(
        'main/dashboard.html',
        flashcard_summary=flashcard_summary,
        quiz_summary=quiz_summary,
        course_summary=course_summary,
        score_overview=score_overview,
        motivation_message=motivation_message,
        quick_actions=quick_actions,
        today_activity=today_activity,
        recent_actions=recent_actions,
    )

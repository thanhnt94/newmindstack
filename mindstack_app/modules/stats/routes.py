# File: mindstack_app/modules/stats/routes.py
# Phiên bản: 2.1
# Mục đích: Bổ sung logic để lấy dữ liệu thống kê cho Khoá học.

from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from . import stats_bp
from ...models import db, User, ScoreLog, FlashcardProgress, QuizProgress, LearningContainer, LearningItem, CourseProgress
from sqlalchemy import func
from datetime import datetime, timedelta, date


def get_leaderboard_data_internal(sort_by, timeframe, viewer=None):
    """Hàm nội bộ để lấy dữ liệu bảng xếp hạng động.

    Args:
        sort_by (str): Tiêu chí sắp xếp.
        timeframe (str): Mốc thời gian lọc dữ liệu.
        viewer (User | None): Người đang xem bảng xếp hạng, dùng để ẩn danh nếu cần.
    """
    today = date.today()
    start_date = None
    if timeframe == 'day':
        start_date = datetime.combine(today, datetime.min.time())
    elif timeframe == 'week':
        start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    elif timeframe == 'month':
        start_date = datetime.combine(today.replace(day=1), datetime.min.time())

    if sort_by != 'total_score':
        return []

    query = db.session.query(
        User.user_id,
        User.username,
        User.user_role,
        func.sum(ScoreLog.score_change).label('value')
    ).join(ScoreLog, User.user_id == ScoreLog.user_id)

    if start_date:
        query = query.filter(ScoreLog.timestamp >= start_date)

    results = (
        query
        .group_by(User.user_id, User.username, User.user_role)
        .order_by(func.sum(ScoreLog.score_change).desc())
        .limit(10)
        .all()
    )

    placeholder_username = 'Người dùng ẩn danh'
    viewer_role = getattr(viewer, 'user_role', None)
    viewer_id = getattr(viewer, 'user_id', None)

    leaderboard_data = []
    for user in results:
        is_anonymous = user.user_role == User.ROLE_ANONYMOUS
        is_viewer = viewer_id is not None and user.user_id == viewer_id
        can_view_real_name = (
            viewer_role == User.ROLE_ADMIN
            or is_viewer
        )
        mask_username = is_anonymous and not can_view_real_name
        display_username = user.username if not mask_username else placeholder_username

        leaderboard_data.append({
            'user_id': user.user_id if not mask_username else None,
            'user_role': user.user_role,
            'username': display_username,
            'display_username': display_username,
            'is_anonymous': is_anonymous,
            'is_username_masked': mask_username,
            'is_viewer': is_viewer,
            'current_period_score': user.value or 0,
            'total_reviews': 0,
            'learned_cards': 0,
            'new_cards_today': 0,
            'total_quiz_answers': 0,
        })

    return leaderboard_data

@stats_bp.route('/')
@login_required
def dashboard():
    """
    Route chính để hiển thị trang dashboard thống kê.
    """
    initial_sort_by = request.args.get('sort_by', 'total_score')
    initial_timeframe = request.args.get('timeframe', 'all_time')
    leaderboard_data = get_leaderboard_data_internal(initial_sort_by, initial_timeframe, viewer=current_user)
    
    # Dữ liệu cho các thẻ thống kê tổng quan
    dashboard_data = {
        # Flashcard
        'flashcard_score': db.session.query(func.sum(ScoreLog.score_change)).filter(ScoreLog.user_id == current_user.user_id, ScoreLog.item_type == 'FLASHCARD').scalar() or 0,
        'learned_distinct_overall': FlashcardProgress.query.filter_by(user_id=current_user.user_id).count(),
        'learned_sets_count': db.session.query(func.count(LearningContainer.container_id.distinct())).join(LearningItem).join(FlashcardProgress).filter(FlashcardProgress.user_id == current_user.user_id, LearningContainer.container_type == 'FLASHCARD_SET').scalar() or 0,
        # Quiz
        'quiz_score': db.session.query(func.sum(ScoreLog.score_change)).filter(ScoreLog.user_id == current_user.user_id, ScoreLog.item_type == 'QUIZ_MCQ').scalar() or 0,
        'questions_answered_count': QuizProgress.query.filter_by(user_id=current_user.user_id).count(),
        'quiz_sets_started_count': db.session.query(func.count(LearningContainer.container_id.distinct())).join(LearningItem).join(QuizProgress).filter(QuizProgress.user_id == current_user.user_id, LearningContainer.container_type == 'QUIZ_SET').scalar() or 0,
        # Course (THÊM MỚI)
        'courses_started_count': db.session.query(func.count(LearningContainer.container_id.distinct())).join(LearningItem).join(CourseProgress).filter(CourseProgress.user_id == current_user.user_id, LearningContainer.container_type == 'COURSE').scalar() or 0,
        'lessons_completed_count': CourseProgress.query.filter_by(user_id=current_user.user_id, completion_percentage=100).count(),
    }

    return render_template(
        'statistics.html',
        leaderboard_data=leaderboard_data,
        dashboard_data=dashboard_data,
        current_sort_by=initial_sort_by,
        current_timeframe=initial_timeframe
    )

@stats_bp.route('/api/leaderboard-data')
@login_required
def get_leaderboard_data_api():
    """API endpoint để tải lại dữ liệu bảng xếp hạng một cách động."""
    sort_by = request.args.get('sort_by', 'total_score')
    timeframe = request.args.get('timeframe', 'all_time')
    data = get_leaderboard_data_internal(sort_by, timeframe, viewer=current_user)
    return jsonify({'success': True, 'data': data})

@stats_bp.route('/api/heatmap-data')
@login_required
def get_heatmap_data_api():
    """API endpoint để cung cấp dữ liệu cho biểu đồ heatmap."""
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    activity = db.session.query(
        func.date(ScoreLog.timestamp).label('date'),
        func.count(ScoreLog.log_id).label('count')
    ).filter(
        ScoreLog.user_id == current_user.user_id,
        ScoreLog.timestamp >= one_year_ago
    ).group_by(func.date(ScoreLog.timestamp)).all()
    
    heatmap_data = {int(datetime.combine(row.date, datetime.min.time()).timestamp()): row.count for row in activity}
    return jsonify(heatmap_data)


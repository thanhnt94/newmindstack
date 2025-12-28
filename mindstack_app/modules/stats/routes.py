# File: mindstack_app/modules/stats/routes.py
# Phiên bản: 2.1
# Mục đích: Bổ sung logic để lấy dữ liệu thống kê cho Khoá học.

from datetime import datetime, timedelta, date, timezone
from collections import defaultdict

from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func, case, or_

from . import stats_bp
from ...models import (
    db,
    User,
    ScoreLog,
    LearningContainer,
    LearningItem,
)
from mindstack_app.models.learning_progress import LearningProgress


ITEM_TYPE_LABELS = {
    'FLASHCARD': 'Flashcard',
    'QUIZ_MCQ': 'Trắc nghiệm',
    'LESSON': 'Bài học',
    'COURSE': 'Khoá học',
}


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


def _get_user_container_options(user_id, container_type, learning_mode, timestamp_attr='last_reviewed', item_type=None):
    """Return the list of learning containers (id/title) a user interacted with.
    
    MIGRATED: Uses LearningProgress with learning_mode filter instead of specific progress models.
    """

    timestamp_column = getattr(LearningProgress, timestamp_attr, None) if timestamp_attr else None

    columns = [
        LearningContainer.container_id.label('container_id'),
        LearningContainer.title.label('title'),
    ]

    if timestamp_column is not None:
        columns.append(func.max(timestamp_column).label('last_activity'))
    else:
        columns.append(func.max(LearningProgress.progress_id).label('last_activity'))

    query = (
        db.session.query(*columns)
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == learning_mode,
            LearningContainer.container_type == container_type,
        )
    )

    if item_type is not None:
        query = query.filter(LearningItem.item_type == item_type)

    order_expression = columns[-1]
    query = query.group_by(LearningContainer.container_id, LearningContainer.title).order_by(order_expression.desc())

    return [
        {
            'id': row.container_id,
            'title': row.title,
        }
        for row in query.all()
    ]


def _sanitize_pagination_args(page, per_page, default_per_page=10, max_per_page=50):
    """Normalise pagination parameters coming from query strings."""

    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    if page < 1:
        page = 1

    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = default_per_page

    if per_page < 1:
        per_page = default_per_page

    per_page = min(per_page, max_per_page)
    return page, per_page


def _resolve_timeframe_dates(timeframe):
    """Return (start_date, end_date) for the requested timeframe."""

    end_date = date.today()
    timeframe = (timeframe or '').lower()
    mapping = {
        '7d': 7,
        '14d': 14,
        '30d': 30,
        '90d': 90,
        '180d': 180,
        '365d': 365,
    }
    if timeframe == 'all':
        return None, end_date

    days = mapping.get(timeframe, 30)
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _normalize_datetime_range(start_date, end_date):
    """Return aware datetime boundaries for filtering timestamps."""

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    else:
        start_dt = None

    if end_date:
        end_dt = (
            datetime.combine(end_date + timedelta(days=1), datetime.min.time())
            .replace(tzinfo=timezone.utc)
        )
    else:
        end_dt = None

    return start_dt, end_dt


def _parse_history_datetime(raw_value):
    """Safely parse ISO formatted timestamps stored in JSON histories."""

    if not raw_value:
        return None

    if isinstance(raw_value, datetime):
        dt_value = raw_value
    elif isinstance(raw_value, str):
        try:
            normalized = raw_value.replace('Z', '+00:00')
            dt_value = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    else:
        dt_value = dt_value.astimezone(timezone.utc)
    return dt_value


def _date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def compute_learning_streaks(user_id):
    """Return (current_streak, longest_streak) in days based on score logs."""

    rows = (
        db.session.query(func.date(ScoreLog.timestamp).label('activity_date'))
        .filter(ScoreLog.user_id == user_id)
        .group_by(func.date(ScoreLog.timestamp))
        .order_by(func.date(ScoreLog.timestamp))
        .all()
    )

    if not rows:
        return 0, 0

    dates = []
    for row in rows:
        value = row.activity_date
        if isinstance(value, datetime):
            value = value.date()
        elif isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                continue
        if isinstance(value, date):
            dates.append(value)

    if not dates:
        return 0, 0

    date_set = set(dates)

    # Current streak: count backwards from today until a gap appears.
    today = date.today()
    current_streak = 0
    pointer = today
    while pointer in date_set:
        current_streak += 1
        pointer -= timedelta(days=1)

    # Longest streak: scan sorted dates.
    longest = 1
    run = 1
    for previous, current in zip(dates, dates[1:]):
        if current == previous + timedelta(days=1):
            run += 1
        else:
            longest = max(longest, run)
            run = 1
    longest = max(longest, run)

    return current_streak, longest


def get_score_trend_series(user_id, timeframe='30d'):
    """Return daily score aggregates for the requested timeframe."""

    start_date, end_date = _resolve_timeframe_dates(timeframe)
    if end_date is None:
        end_date = date.today()

    # Determine range when the user requests "all" but has limited history.
    if start_date is None:
        earliest_date = (
            db.session.query(func.min(func.date(ScoreLog.timestamp)))
            .filter(ScoreLog.user_id == user_id)
            .scalar()
        )
        if earliest_date is None:
            return {
                'timeframe': timeframe,
                'series': [],
                'total_score': 0,
                'average_daily_score': 0,
            }
        start_date = earliest_date

    start_dt, end_dt = _normalize_datetime_range(start_date, end_date)

    flashcard_case = case((ScoreLog.item_type == 'FLASHCARD', ScoreLog.score_change), else_=0)
    quiz_case = case((ScoreLog.item_type == 'QUIZ_MCQ', ScoreLog.score_change), else_=0)
    course_case = case((ScoreLog.item_type.in_(['LESSON', 'COURSE']), ScoreLog.score_change), else_=0)

    rows = (
        db.session.query(
            func.date(ScoreLog.timestamp).label('activity_date'),
            func.sum(ScoreLog.score_change).label('total_score'),
            func.sum(flashcard_case).label('flashcard_score'),
            func.sum(quiz_case).label('quiz_score'),
            func.sum(course_case).label('course_score'),
        )
        .filter(ScoreLog.user_id == user_id)
        .filter(ScoreLog.timestamp >= start_dt)
        .filter(ScoreLog.timestamp < end_dt)
        .group_by(func.date(ScoreLog.timestamp))
        .order_by(func.date(ScoreLog.timestamp))
        .all()
    )

    if not rows:
        return {
            'timeframe': timeframe,
            'series': [],
            'total_score': 0,
            'average_daily_score': 0,
        }

    row_map = {row.activity_date: row for row in rows}

    series = []
    cumulative_total = 0
    total_score = 0

    for current_date in _date_range(start_date, end_date):
        row = row_map.get(current_date)
        total = int(row.total_score or 0) if row else 0
        flashcard_total = int(row.flashcard_score or 0) if row else 0
        quiz_total = int(row.quiz_score or 0) if row else 0
        course_total = int(row.course_score or 0) if row else 0
        other_total = total - flashcard_total - quiz_total - course_total

        cumulative_total += total
        total_score += total

        series.append({
            'date': current_date.isoformat(),
            'total_score': total,
            'flashcard_score': flashcard_total,
            'quiz_score': quiz_total,
            'course_score': course_total,
            'other_score': other_total,
            'cumulative_score': cumulative_total,
        })

    average_daily_score = round(total_score / len(series), 1) if series else 0

    return {
        'timeframe': timeframe,
        'series': series,
        'total_score': total_score,
        'average_daily_score': average_daily_score,
    }


def get_activity_breakdown(user_id, timeframe='30d'):
    """Aggregate score entries by item type for the timeframe."""

    start_date, end_date = _resolve_timeframe_dates(timeframe)
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        earliest_date = (
            db.session.query(func.min(func.date(ScoreLog.timestamp)))
            .filter(ScoreLog.user_id == user_id)
            .scalar()
        )
        if earliest_date is None:
            return {
                'timeframe': timeframe,
                'total_entries': 0,
                'total_score': 0,
                'average_score_per_entry': 0,
                'buckets': [],
            }
        start_date = earliest_date

    start_dt, end_dt = _normalize_datetime_range(start_date, end_date)

    rows = (
        db.session.query(
            ScoreLog.item_type.label('item_type'),
            func.count(ScoreLog.log_id).label('entry_count'),
            func.sum(ScoreLog.score_change).label('score_total'),
        )
        .filter(ScoreLog.user_id == user_id)
        .filter(ScoreLog.timestamp >= start_dt)
        .filter(ScoreLog.timestamp < end_dt)
        .group_by(ScoreLog.item_type)
        .all()
    )

    buckets = []
    total_entries = 0
    total_score = 0

    for row in rows:
        item_type = row.item_type or 'OTHER'
        entries = int(row.entry_count or 0)
        score = int(row.score_total or 0)
        total_entries += entries
        total_score += score
        buckets.append({
            'item_type': item_type,
            'label': ITEM_TYPE_LABELS.get(item_type, 'Hoạt động khác'),
            'entries': entries,
            'score': score,
        })

    buckets.sort(key=lambda bucket: bucket['score'], reverse=True)
    average_score_per_entry = round(total_score / total_entries, 2) if total_entries else 0

    return {
        'timeframe': timeframe,
        'total_entries': total_entries,
        'total_score': total_score,
        'average_score_per_entry': average_score_per_entry,
        'buckets': buckets,
    }


def _build_flashcard_items_query(user_id):
    # MIGRATED: Use LearningProgress with MODE_FLASHCARD
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            LearningProgress.status.label('status'),
            LearningProgress.last_reviewed.label('last_reviewed'),
            LearningProgress.first_seen.label('first_seen'),
            LearningProgress.due_time.label('due_time'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningItem.item_type == 'FLASHCARD',
            LearningContainer.container_type == 'FLASHCARD_SET',
        )
    )


def _apply_flashcard_category_filter(query, status):
    # MIGRATED: Use LearningProgress instead of FlashcardProgress
    if not status or status == 'all':
        return query

    status = status.lower()
    if status in {'new', 'learning', 'mastered', 'hard'}:
        return query.filter(LearningProgress.status == status)

    if status == 'needs_review':
        now = datetime.utcnow()
        return query.filter(
            LearningProgress.due_time.isnot(None),
            LearningProgress.due_time <= now,
        )

    if status == 'due_soon':
        now = datetime.utcnow()
        return query.filter(
            LearningProgress.due_time.isnot(None),
            LearningProgress.due_time <= now + timedelta(days=1),
        )

    return query


def paginate_flashcard_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of FlashcardProgress
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_flashcard_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_flashcard_category_filter(query, status)

    total = query.with_entities(func.count(LearningProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(LearningProgress.last_reviewed, LearningProgress.first_seen).desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    records = []
    for row in rows:
        content = row.content or {}
        records.append({
            'container_id': row.container_id,
            'container_title': row.container_title,
            'item_id': row.item_id,
            'front': content.get('front'),
            'back': content.get('back'),
            'status': row.status,
            'last_reviewed': row.last_reviewed.isoformat() if row.last_reviewed else None,
            'first_seen': row.first_seen.isoformat() if row.first_seen else None,
            'due_time': row.due_time.isoformat() if row.due_time else None,
        })

    return {
        'status': status or 'all',
        'page': page,
        'per_page': per_page,
        'total': int(total),
        'records': records,
    }


def _build_quiz_items_query(user_id):
    # MIGRATED: Use LearningProgress with MODE_QUIZ
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            LearningProgress.status.label('status'),
            LearningProgress.last_reviewed.label('last_reviewed'),
            LearningProgress.first_seen.label('first_seen'),
            LearningProgress.times_correct.label('times_correct'),
            LearningProgress.times_incorrect.label('times_incorrect'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ,
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningContainer.container_type == 'QUIZ_SET',
        )
    )


def _apply_quiz_category_filter(query, status):
    # MIGRATED: Use LearningProgress instead of QuizProgress
    if not status or status == 'all':
        return query

    status = status.lower()
    if status in {'new', 'learning', 'mastered', 'hard'}:
        return query.filter(LearningProgress.status == status)

    if status == 'needs_review':
        return query.filter(
            or_(
                LearningProgress.status.in_({'learning', 'hard'}),
                LearningProgress.times_incorrect > LearningProgress.times_correct,
            )
        )

    return query


def paginate_quiz_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of QuizProgress
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_quiz_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_quiz_category_filter(query, status)

    total = query.with_entities(func.count(LearningProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(LearningProgress.last_reviewed, LearningProgress.first_seen).desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    records = []
    for row in rows:
        content = row.content or {}
        records.append({
            'container_id': row.container_id,
            'container_title': row.container_title,
            'item_id': row.item_id,
            'question': content.get('question'),
            'status': row.status,
            'times_correct': int(row.times_correct or 0),
            'times_incorrect': int(row.times_incorrect or 0),
            'last_reviewed': row.last_reviewed.isoformat() if row.last_reviewed else None,
            'first_seen': row.first_seen.isoformat() if row.first_seen else None,
        })

    return {
        'status': status or 'all',
        'page': page,
        'per_page': per_page,
        'total': int(total),
        'records': records,
    }


def _build_course_items_query(user_id):
    # MIGRATED: Use LearningProgress with MODE_COURSE
    # Note: completion_percentage is stored in mode_data or approximated via mastery
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            LearningProgress.mastery.label('mastery'),  # mastery * 100 = completion_percentage
            LearningProgress.last_reviewed.label('last_updated'),
            LearningProgress.mode_data.label('mode_data'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
            LearningItem.item_type == 'LESSON',
            LearningContainer.container_type == 'COURSE',
        )
    )


def _apply_course_category_filter(query, status):
    # MIGRATED: Use LearningProgress.mastery instead of CourseProgress.completion_percentage
    # mastery >= 1.0 means 100% complete
    if not status or status == 'all':
        return query

    status = status.lower()
    if status == 'completed':
        return query.filter(LearningProgress.mastery >= 1.0)
    if status == 'in_progress':
        return query.filter(
            LearningProgress.mastery > 0,
            LearningProgress.mastery < 1.0,
        )
    if status == 'not_started':
        return query.filter(LearningProgress.mastery == 0)

    return query


def paginate_course_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of CourseProgress
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_course_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_course_category_filter(query, status)

    total = query.with_entities(func.count(LearningProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(LearningProgress.last_reviewed, LearningProgress.progress_id).desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    records = []
    for row in rows:
        content = row.content or {}
        # Extract completion_percentage from mode_data or calculate from mastery
        mode_data = row.mode_data or {}
        completion_pct = mode_data.get('completion_percentage', int((row.mastery or 0) * 100))
        records.append({
            'container_id': row.container_id,
            'container_title': row.container_title,
            'item_id': row.item_id,
            'title': content.get('title') or content.get('lesson_title'),
            'status': 'completed' if completion_pct >= 100 else (
                'in_progress' if completion_pct > 0 else 'not_started'
            ),
            'completion_percentage': completion_pct,
            'last_updated': row.last_updated.isoformat() if row.last_updated else None,
        })

    return {
        'status': status or 'all',
        'page': page,
        'per_page': per_page,
        'total': int(total),
        'records': records,
    }


def get_flashcard_activity_series(user_id, container_id, timeframe='30d'):
    # MIGRATED: Use LearningProgress with MODE_FLASHCARD
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    query = (
        db.session.query(LearningProgress.mode_data)
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    histories = query.all()
    for (mode_data,) in histories:
        # Extract review_history from mode_data
        history = (mode_data or {}).get('review_history', []) if mode_data else []
        if not history or not isinstance(history, list):
            continue

        parsed_entries = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            dt_value = _parse_history_datetime(entry.get('timestamp'))
            if not dt_value:
                continue
            parsed_entries.append((dt_value, entry))
            entry_date = dt_value.date()
            if min_date_seen is None or entry_date < min_date_seen:
                min_date_seen = entry_date

        parsed_entries.sort(key=lambda item: item[0])

        seen_new = False
        for dt_value, entry in parsed_entries:
            entry_date = dt_value.date()
            if timeframe_start and entry_date < timeframe_start:
                continue
            if entry_date > timeframe_end:
                continue

            if not seen_new:
                new_counts[entry_date] += 1
                seen_new = True

            if entry.get('type') != 'preview':
                review_counts[entry_date] += 1

    if timeframe_start is None:
        if min_date_seen is None:
            return {'series': []}
        timeframe_start = min_date_seen

    start_dt_filter = datetime.combine(timeframe_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt_filter = datetime.combine(timeframe_end + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

    score_rows = (
        db.session.query(
            func.date(ScoreLog.timestamp).label('activity_date'),
            func.sum(ScoreLog.score_change).label('total_score'),
        )
        .join(LearningItem, LearningItem.item_id == ScoreLog.item_id)
        .filter(
            ScoreLog.user_id == user_id,
            ScoreLog.item_type == 'FLASHCARD',
            LearningItem.container_id == container_id,
            ScoreLog.timestamp >= start_dt_filter,
            ScoreLog.timestamp < end_dt_filter,
        )
        .group_by(func.date(ScoreLog.timestamp))
        .all()
    )

    score_map = {row.activity_date: int(row.total_score or 0) for row in score_rows}

    series = []
    for current_date in _date_range(timeframe_start, timeframe_end):
        series.append({
            'date': current_date.isoformat(),
            'new_count': int(new_counts.get(current_date, 0)),
            'review_count': int(review_counts.get(current_date, 0)),
            'score': int(score_map.get(current_date, 0)),
        })

    return {
        'series': series,
        'start_date': timeframe_start.isoformat(),
        'end_date': timeframe_end.isoformat(),
        'timeframe': timeframe or '30d',
    }


def get_quiz_activity_series(user_id, container_id, timeframe='30d'):
    # MIGRATED: Use LearningProgress with MODE_QUIZ
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    query = (
        db.session.query(LearningProgress.mode_data)
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    histories = query.all()
    for (mode_data,) in histories:
        # Extract review_history from mode_data
        history = (mode_data or {}).get('review_history', []) if mode_data else []
        if not history or not isinstance(history, list):
            continue

        parsed_entries = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            dt_value = _parse_history_datetime(entry.get('timestamp'))
            if not dt_value:
                continue
            parsed_entries.append((dt_value, entry))
            entry_date = dt_value.date()
            if min_date_seen is None or entry_date < min_date_seen:
                min_date_seen = entry_date

        parsed_entries.sort(key=lambda item: item[0])

        first_entry_date = parsed_entries[0][0].date() if parsed_entries else None
        for index, (dt_value, _) in enumerate(parsed_entries):
            entry_date = dt_value.date()
            if timeframe_start and entry_date < timeframe_start:
                continue
            if entry_date > timeframe_end:
                continue

            if index == 0 and first_entry_date == entry_date:
                new_counts[entry_date] += 1
            else:
                review_counts[entry_date] += 1

    if timeframe_start is None:
        if min_date_seen is None:
            return {'series': []}
        timeframe_start = min_date_seen

    start_dt_filter = datetime.combine(timeframe_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt_filter = datetime.combine(timeframe_end + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

    score_rows = (
        db.session.query(
            func.date(ScoreLog.timestamp).label('activity_date'),
            func.sum(ScoreLog.score_change).label('total_score'),
        )
        .join(LearningItem, LearningItem.item_id == ScoreLog.item_id)
        .filter(
            ScoreLog.user_id == user_id,
            ScoreLog.item_type == 'QUIZ_MCQ',
            LearningItem.container_id == container_id,
            ScoreLog.timestamp >= start_dt_filter,
            ScoreLog.timestamp < end_dt_filter,
        )
        .group_by(func.date(ScoreLog.timestamp))
        .all()
    )

    score_map = {row.activity_date: int(row.total_score or 0) for row in score_rows}

    series = []
    for current_date in _date_range(timeframe_start, timeframe_end):
        series.append({
            'date': current_date.isoformat(),
            'new_count': int(new_counts.get(current_date, 0)),
            'review_count': int(review_counts.get(current_date, 0)),
            'score': int(score_map.get(current_date, 0)),
        })

    return {
        'series': series,
        'start_date': timeframe_start.isoformat(),
        'end_date': timeframe_end.isoformat(),
        'timeframe': timeframe or '30d',
    }


def get_course_activity_series(user_id, container_id, timeframe='30d'):
    # MIGRATED: Use LearningProgress with MODE_COURSE
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)

    query = (
        db.session.query(LearningProgress.last_reviewed, LearningProgress.mastery, LearningProgress.mode_data)
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    for last_updated, mastery, mode_data in query.all():
        dt_value = _parse_history_datetime(last_updated)
        if not dt_value:
            continue
        entry_date = dt_value.date()
        if min_date_seen is None or entry_date < min_date_seen:
            min_date_seen = entry_date

        if timeframe_start and entry_date < timeframe_start:
            continue
        if entry_date > timeframe_end:
            continue

        # Get completion_percentage from mode_data or mastery
        mode_data_dict = mode_data or {}
        completion_percentage = mode_data_dict.get('completion_percentage', int((mastery or 0) * 100))
        if completion_percentage and completion_percentage > 0:
            new_counts[entry_date] += 1
        if completion_percentage and completion_percentage >= 100:
            review_counts[entry_date] += 1

    if timeframe_start is None:
        if min_date_seen is None:
            return {'series': []}
        timeframe_start = min_date_seen

    series = []
    for current_date in _date_range(timeframe_start, timeframe_end):
        series.append({
            'date': current_date.isoformat(),
            'new_count': int(new_counts.get(current_date, 0)),
            'review_count': int(review_counts.get(current_date, 0)),
            'score': 0,
        })

    return {
        'series': series,
        'start_date': timeframe_start.isoformat(),
        'end_date': timeframe_end.isoformat(),
        'timeframe': timeframe or '30d',
    }


def get_flashcard_set_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate flashcard metrics per set for the provided user.
    
    MIGRATED: Uses LearningProgress with MODE_FLASHCARD.
    """

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningContainer.container_type == 'FLASHCARD_SET',
            LearningItem.item_type == 'FLASHCARD',
        )
    )

    if container_id is not None:
        container_query = container_query.filter(LearningContainer.container_id == container_id)

    containers = (
        container_query
        .group_by(LearningContainer.container_id, LearningContainer.title)
        .all()
    )

    if not containers:
        return {}

    container_ids = [row.container_id for row in containers]
    title_map = {row.container_id: row.title for row in containers}

    total_cards_map = dict(
        db.session.query(
            LearningItem.container_id,
            func.count(LearningItem.item_id).label('total_cards'),
        )
        .filter(
            LearningItem.item_type == 'FLASHCARD',
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_rows = (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            func.count(LearningProgress.progress_id).label('studied_cards'),
            func.sum(case((LearningProgress.status == 'mastered', 1), else_=0)).label('learned_cards'),
            func.sum(LearningProgress.times_correct).label('total_correct'),
            func.sum(LearningProgress.times_incorrect).label('total_incorrect'),
            func.sum(LearningProgress.times_vague).label('total_vague'),
            func.avg(LearningProgress.correct_streak).label('avg_correct_streak'),
            func.max(LearningProgress.correct_streak).label('best_correct_streak'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_map = {row.container_id: row for row in progress_rows}

    items_payload_map = {}
    target_ids = container_ids if container_id is None else [container_id]
    for target_id in target_ids:
        items_payload_map[target_id] = paginate_flashcard_items(
            user_id,
            container_id=target_id,
            status=status,
            page=page,
            per_page=per_page,
        )

    result = {}
    for container_id in container_ids:
        progress = progress_map.get(container_id)
        total_cards = int(total_cards_map.get(container_id, 0) or 0)

        studied_cards = int(progress.studied_cards or 0) if progress else 0
        learned_cards = int(progress.learned_cards or 0) if progress else 0
        total_correct = int(progress.total_correct or 0) if progress else 0
        total_incorrect = int(progress.total_incorrect or 0) if progress else 0
        total_vague = int(progress.total_vague or 0) if progress else 0
        total_attempts = total_correct + total_incorrect + total_vague

        accuracy_percent = None
        if total_attempts > 0:
            accuracy_percent = round((total_correct / total_attempts) * 100, 1)

        avg_streak = float(progress.avg_correct_streak or 0) if progress and progress.avg_correct_streak is not None else 0.0
        best_streak = int(progress.best_correct_streak or 0) if progress else 0

        result[container_id] = {
            'container_id': container_id,
            'container_title': title_map.get(container_id),
            'total_cards': total_cards,
            'studied_cards': studied_cards,
            'learned_cards': learned_cards,
            'accuracy_percent': accuracy_percent,
            'avg_correct_streak': round(avg_streak, 1) if avg_streak else 0.0,
            'best_correct_streak': best_streak,
            'items': items_payload_map.get(container_id, {
                'status': status or 'all',
                'page': page,
                'per_page': per_page,
                'total': 0,
                'records': [],
            }),
        }

    return result


def get_quiz_set_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate quiz metrics per set for the provided user.
    
    MIGRATED: Uses LearningProgress with MODE_QUIZ.
    """

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ,
            LearningContainer.container_type == 'QUIZ_SET',
            LearningItem.item_type == 'QUIZ_MCQ',
        )
    )

    if container_id is not None:
        container_query = container_query.filter(LearningContainer.container_id == container_id)

    containers = (
        container_query
        .group_by(LearningContainer.container_id, LearningContainer.title)
        .all()
    )

    if not containers:
        return {}

    container_ids = [row.container_id for row in containers]
    title_map = {row.container_id: row.title for row in containers}

    total_questions_map = dict(
        db.session.query(
            LearningItem.container_id,
            func.count(LearningItem.item_id).label('total_questions'),
        )
        .filter(
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_rows = (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            func.count(LearningProgress.progress_id).label('attempted_questions'),
            func.sum(LearningProgress.times_correct).label('total_correct'),
            func.sum(LearningProgress.times_incorrect).label('total_incorrect'),
            func.avg(LearningProgress.correct_streak).label('avg_correct_streak'),
            func.max(LearningProgress.correct_streak).label('best_correct_streak'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_QUIZ,
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_map = {row.container_id: row for row in progress_rows}

    items_payload_map = {}
    target_ids = container_ids if container_id is None else [container_id]
    for target_id in target_ids:
        items_payload_map[target_id] = paginate_quiz_items(
            user_id,
            container_id=target_id,
            status=status,
            page=page,
            per_page=per_page,
        )

    result = {}
    for container_id in container_ids:
        progress = progress_map.get(container_id)
        total_questions = int(total_questions_map.get(container_id, 0) or 0)

        attempted = int(progress.attempted_questions or 0) if progress else 0
        total_correct = int(progress.total_correct or 0) if progress else 0
        total_incorrect = int(progress.total_incorrect or 0) if progress else 0
        total_attempts = total_correct + total_incorrect

        accuracy_percent = None
        if total_attempts > 0:
            accuracy_percent = round((total_correct / total_attempts) * 100, 1)

        avg_streak = float(progress.avg_correct_streak or 0) if progress and progress.avg_correct_streak is not None else 0.0
        best_streak = int(progress.best_correct_streak or 0) if progress else 0

        result[container_id] = {
            'container_id': container_id,
            'container_title': title_map.get(container_id),
            'total_questions': total_questions,
            'attempted_questions': attempted,
            'total_correct': total_correct,
            'total_incorrect': total_incorrect,
            'accuracy_percent': accuracy_percent,
            'avg_correct_streak': round(avg_streak, 1) if avg_streak else 0.0,
            'best_correct_streak': best_streak,
            'items': items_payload_map.get(container_id, {
                'status': status or 'all',
                'page': page,
                'per_page': per_page,
                'total': 0,
                'records': [],
            }),
        }

    return result


def get_course_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate course metrics per set for the provided user.
    
    MIGRATED: Uses LearningProgress with MODE_COURSE.
    """

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(LearningProgress, LearningProgress.item_id == LearningItem.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
            LearningContainer.container_type == 'COURSE',
            LearningItem.item_type == 'LESSON',
        )
    )

    if container_id is not None:
        container_query = container_query.filter(LearningContainer.container_id == container_id)

    containers = (
        container_query
        .group_by(LearningContainer.container_id, LearningContainer.title)
        .all()
    )

    if not containers:
        return {}

    container_ids = [row.container_id for row in containers]
    title_map = {row.container_id: row.title for row in containers}

    total_lessons_map = dict(
        db.session.query(
            LearningItem.container_id,
            func.count(LearningItem.item_id).label('total_lessons'),
        )
        .filter(
            LearningItem.item_type == 'LESSON',
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_rows = (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            func.count(LearningProgress.progress_id).label('lessons_started'),
            func.sum(case((LearningProgress.mastery >= 1.0, 1), else_=0)).label('lessons_completed'),
            func.avg(LearningProgress.mastery * 100).label('avg_completion'),
            func.max(LearningProgress.last_reviewed).label('last_activity'),
        )
        .join(LearningItem, LearningItem.item_id == LearningProgress.item_id)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_COURSE,
            LearningItem.container_id.in_(container_ids),
        )
        .group_by(LearningItem.container_id)
        .all()
    )

    progress_map = {row.container_id: row for row in progress_rows}

    items_payload_map = {}
    target_ids = container_ids if container_id is None else [container_id]
    for target_id in target_ids:
        items_payload_map[target_id] = paginate_course_items(
            user_id,
            container_id=target_id,
            status=status,
            page=page,
            per_page=per_page,
        )

    result = {}
    for container_id in container_ids:
        progress = progress_map.get(container_id)
        total_lessons = int(total_lessons_map.get(container_id, 0) or 0)

        lessons_started = int(progress.lessons_started or 0) if progress else 0
        lessons_completed = int(progress.lessons_completed or 0) if progress else 0
        avg_completion = float(progress.avg_completion or 0) if progress and progress.avg_completion is not None else 0.0
        last_activity_value = progress.last_activity.isoformat() if progress and progress.last_activity else None

        result[container_id] = {
            'container_id': container_id,
            'container_title': title_map.get(container_id),
            'total_lessons': total_lessons,
            'lessons_started': lessons_started,
            'lessons_completed': lessons_completed,
            'avg_completion_percent': round(avg_completion, 1) if avg_completion else 0.0,
            'last_activity': last_activity_value,
            'items': items_payload_map.get(container_id, {
                'status': status or 'all',
                'page': page,
                'per_page': per_page,
                'total': 0,
                'records': [],
            }),
        }

    return result

@stats_bp.route('/')
@login_required
def dashboard():
    """
    Route chính để hiển thị trang dashboard thống kê.
    """
    initial_sort_by = request.args.get('sort_by', 'total_score')
    initial_timeframe = request.args.get('timeframe', 'all_time')
    leaderboard_data = get_leaderboard_data_internal(initial_sort_by, initial_timeframe, viewer=current_user)
    
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

    flashcard_sets = _get_user_container_options(
        current_user.user_id,
        'FLASHCARD_SET',
        FlashcardProgress,
        'last_reviewed',
        item_type='FLASHCARD',
    )
    quiz_sets = _get_user_container_options(
        current_user.user_id,
        'QUIZ_SET',
        QuizProgress,
        'last_reviewed',
        item_type='QUIZ_MCQ',
    )
    course_sets = _get_user_container_options(
        current_user.user_id,
        'COURSE',
        CourseProgress,
        'last_updated',
        item_type='LESSON',
    )

    return render_template(
        'statistics.html',
        leaderboard_data=leaderboard_data,
        dashboard_data=dashboard_data,
        current_sort_by=initial_sort_by,
        current_timeframe=initial_timeframe,
        flashcard_sets=flashcard_sets,
        quiz_sets=quiz_sets,
        course_sets=course_sets,
        recent_activity=recent_activity,
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


@stats_bp.route('/api/score-trend')
@login_required
def get_score_trend_api():
    timeframe = request.args.get('timeframe', '30d')
    data = get_score_trend_series(current_user.user_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/activity-breakdown')
@login_required
def get_activity_breakdown_api():
    timeframe = request.args.get('timeframe', '30d')
    data = get_activity_breakdown(current_user.user_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-activity')
@login_required
def get_flashcard_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_flashcard_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-activity')
@login_required
def get_quiz_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_quiz_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-activity')
@login_required
def get_course_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_course_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-set-metrics')
@login_required
def get_flashcard_set_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_flashcard_set_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-set-metrics')
@login_required
def get_quiz_set_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_quiz_set_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-metrics')
@login_required
def get_course_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_course_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-items')
@login_required
def get_flashcard_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_flashcard_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-items')
@login_required
def get_quiz_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_quiz_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-items')
@login_required
def get_course_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = _sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_course_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


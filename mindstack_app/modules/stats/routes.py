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
    FlashcardProgress,
    QuizProgress,
    LearningContainer,
    LearningItem,
    CourseProgress,
)


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


def _get_user_container_options(user_id, container_type, progress_model, timestamp_attr, item_type=None):
    """Return the list of learning containers (id/title) a user interacted with."""

    timestamp_column = getattr(progress_model, timestamp_attr, None) if timestamp_attr else None

    columns = [
        LearningContainer.container_id.label('container_id'),
        LearningContainer.title.label('title'),
    ]

    if timestamp_column is not None:
        columns.append(func.max(timestamp_column).label('last_activity'))
    else:
        columns.append(func.max(progress_model.progress_id).label('last_activity'))

    query = (
        db.session.query(*columns)
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(progress_model, progress_model.item_id == LearningItem.item_id)
        .filter(
            progress_model.user_id == user_id,
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


def _build_flashcard_items_query(user_id):
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            FlashcardProgress.status.label('status'),
            FlashcardProgress.last_reviewed.label('last_reviewed'),
            FlashcardProgress.first_seen_timestamp.label('first_seen'),
            FlashcardProgress.due_time.label('due_time'),
        )
        .join(LearningItem, LearningItem.item_id == FlashcardProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            FlashcardProgress.user_id == user_id,
            LearningItem.item_type == 'FLASHCARD',
            LearningContainer.container_type == 'FLASHCARD_SET',
        )
    )


def _apply_flashcard_category_filter(query, status):
    if not status or status == 'all':
        return query

    status = status.lower()
    if status in {'new', 'learning', 'mastered', 'hard'}:
        return query.filter(FlashcardProgress.status == status)

    if status == 'needs_review':
        now = datetime.utcnow()
        return query.filter(
            FlashcardProgress.due_time.isnot(None),
            FlashcardProgress.due_time <= now,
        )

    if status == 'due_soon':
        now = datetime.utcnow()
        return query.filter(
            FlashcardProgress.due_time.isnot(None),
            FlashcardProgress.due_time <= now + timedelta(days=1),
        )

    return query


def paginate_flashcard_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_flashcard_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_flashcard_category_filter(query, status)

    total = query.with_entities(func.count(FlashcardProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(FlashcardProgress.last_reviewed, FlashcardProgress.first_seen_timestamp).desc())
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
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            QuizProgress.status.label('status'),
            QuizProgress.last_reviewed.label('last_reviewed'),
            QuizProgress.first_seen_timestamp.label('first_seen'),
            QuizProgress.times_correct.label('times_correct'),
            QuizProgress.times_incorrect.label('times_incorrect'),
        )
        .join(LearningItem, LearningItem.item_id == QuizProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            QuizProgress.user_id == user_id,
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningContainer.container_type == 'QUIZ_SET',
        )
    )


def _apply_quiz_category_filter(query, status):
    if not status or status == 'all':
        return query

    status = status.lower()
    if status in {'new', 'learning', 'mastered', 'hard'}:
        return query.filter(QuizProgress.status == status)

    if status == 'needs_review':
        return query.filter(
            or_(
                QuizProgress.status.in_({'learning', 'hard'}),
                QuizProgress.times_incorrect > QuizProgress.times_correct,
            )
        )

    return query


def paginate_quiz_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_quiz_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_quiz_category_filter(query, status)

    total = query.with_entities(func.count(QuizProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(QuizProgress.last_reviewed, QuizProgress.first_seen_timestamp).desc())
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
    return (
        db.session.query(
            LearningItem.container_id.label('container_id'),
            LearningContainer.title.label('container_title'),
            LearningItem.item_id.label('item_id'),
            LearningItem.content.label('content'),
            CourseProgress.completion_percentage.label('completion_percentage'),
            CourseProgress.last_updated.label('last_updated'),
        )
        .join(LearningItem, LearningItem.item_id == CourseProgress.item_id)
        .join(LearningContainer, LearningContainer.container_id == LearningItem.container_id)
        .filter(
            CourseProgress.user_id == user_id,
            LearningItem.item_type == 'LESSON',
            LearningContainer.container_type == 'COURSE',
        )
    )


def _apply_course_category_filter(query, status):
    if not status or status == 'all':
        return query

    status = status.lower()
    if status == 'completed':
        return query.filter(CourseProgress.completion_percentage >= 100)
    if status == 'in_progress':
        return query.filter(
            CourseProgress.completion_percentage > 0,
            CourseProgress.completion_percentage < 100,
        )
    if status == 'not_started':
        return query.filter(CourseProgress.completion_percentage == 0)

    return query


def paginate_course_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = _sanitize_pagination_args(page, per_page)
    query = _build_course_items_query(user_id)

    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)

    query = _apply_course_category_filter(query, status)

    total = query.with_entities(func.count(CourseProgress.progress_id)).scalar() or 0

    rows = (
        query
        .order_by(func.coalesce(CourseProgress.last_updated, CourseProgress.progress_id).desc())
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
            'title': content.get('title') or content.get('lesson_title'),
            'status': 'completed' if int(row.completion_percentage or 0) >= 100 else (
                'in_progress' if int(row.completion_percentage or 0) > 0 else 'not_started'
            ),
            'completion_percentage': int(row.completion_percentage or 0),
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
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    query = (
        db.session.query(FlashcardProgress.review_history)
        .join(LearningItem, LearningItem.item_id == FlashcardProgress.item_id)
        .filter(
            FlashcardProgress.user_id == user_id,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    histories = query.all()
    for (history,) in histories:
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
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    query = (
        db.session.query(QuizProgress.review_history)
        .join(LearningItem, LearningItem.item_id == QuizProgress.item_id)
        .filter(
            QuizProgress.user_id == user_id,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    histories = query.all()
    for (history,) in histories:
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
    if not container_id:
        return {'series': []}

    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)

    query = (
        db.session.query(CourseProgress.last_updated, CourseProgress.completion_percentage)
        .join(LearningItem, LearningItem.item_id == CourseProgress.item_id)
        .filter(
            CourseProgress.user_id == user_id,
            LearningItem.container_id == container_id,
        )
    )

    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    min_date_seen = None

    for last_updated, completion_percentage in query.all():
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
    """Aggregate flashcard metrics per set for the provided user."""

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(FlashcardProgress, FlashcardProgress.item_id == LearningItem.item_id)
        .filter(
            FlashcardProgress.user_id == user_id,
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
            func.count(FlashcardProgress.progress_id).label('studied_cards'),
            func.sum(case((FlashcardProgress.status == 'mastered', 1), else_=0)).label('learned_cards'),
            func.sum(FlashcardProgress.times_correct).label('total_correct'),
            func.sum(FlashcardProgress.times_incorrect).label('total_incorrect'),
            func.sum(FlashcardProgress.times_vague).label('total_vague'),
            func.avg(FlashcardProgress.correct_streak).label('avg_correct_streak'),
            func.max(FlashcardProgress.correct_streak).label('best_correct_streak'),
        )
        .join(LearningItem, LearningItem.item_id == FlashcardProgress.item_id)
        .filter(
            FlashcardProgress.user_id == user_id,
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
    """Aggregate quiz metrics per set for the provided user."""

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(QuizProgress, QuizProgress.item_id == LearningItem.item_id)
        .filter(
            QuizProgress.user_id == user_id,
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
            func.count(QuizProgress.progress_id).label('attempted_questions'),
            func.sum(QuizProgress.times_correct).label('total_correct'),
            func.sum(QuizProgress.times_incorrect).label('total_incorrect'),
            func.avg(QuizProgress.correct_streak).label('avg_correct_streak'),
            func.max(QuizProgress.correct_streak).label('best_correct_streak'),
        )
        .join(LearningItem, LearningItem.item_id == QuizProgress.item_id)
        .filter(
            QuizProgress.user_id == user_id,
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
    """Aggregate course metrics per set for the provided user."""

    container_query = (
        db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
        )
        .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
        .join(CourseProgress, CourseProgress.item_id == LearningItem.item_id)
        .filter(
            CourseProgress.user_id == user_id,
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
            func.count(CourseProgress.progress_id).label('lessons_started'),
            func.sum(case((CourseProgress.completion_percentage >= 100, 1), else_=0)).label('lessons_completed'),
            func.avg(CourseProgress.completion_percentage).label('avg_completion'),
            func.max(CourseProgress.last_updated).label('last_activity'),
        )
        .join(LearningItem, LearningItem.item_id == CourseProgress.item_id)
        .filter(
            CourseProgress.user_id == user_id,
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


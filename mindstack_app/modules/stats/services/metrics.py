# File: mindstack_app/modules/stats/routes.py
# PhiÃªn báº£n: 2.1
# Má»¥c Ä‘Ã­ch: Bá»• sung logic Ä‘á»ƒ láº¥y dá»¯ liá»‡u thá»‘ng kÃª cho KhoÃ¡ há»c.

from datetime import datetime, timedelta, date, timezone
from collections import defaultdict

from sqlalchemy import func, case, or_

from mindstack_app.models import (
    db,
    User,
    ScoreLog,
    LearningContainer,
    LearningItem,
)
from mindstack_app.models.learning_progress import LearningProgress


ITEM_TYPE_LABELS = {
    'FLASHCARD': 'Flashcard',
    'QUIZ_MCQ': 'Tráº¯c nghiá»‡m',
    'LESSON': 'BÃ i há»c',
    'COURSE': 'KhoÃ¡ há»c',
}



def get_user_container_options(user_id, container_type, learning_mode, timestamp_attr='fsrs_last_review', item_type=None):
    """Return the list of learning containers (id/title) a user interacted with.
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


def sanitize_pagination_args(page, per_page, default_per_page=10, max_per_page=50):
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
            'label': ITEM_TYPE_LABELS.get(item_type, 'Hoáº¡t Ä‘á»™ng khÃ¡c'),
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
            LearningProgress.fsrs_state.label('fsrs_state'),
            LearningProgress.fsrs_stability.label('fsrs_stability'),
            LearningProgress.fsrs_difficulty.label('fsrs_difficulty'),
            LearningProgress.fsrs_last_review.label('last_reviewed'),
            LearningProgress.first_seen.label('first_seen'),
            LearningProgress.fsrs_due.label('due_time'),
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
    # MIGRATED: Use FSRS Native columns map logic
    if not status or status == 'all':
        return query

    status = status.lower()
    
    if status == 'new':
        return query.filter(LearningProgress.fsrs_state == LearningProgress.STATE_NEW)
    if status == 'learning':
        return query.filter(LearningProgress.fsrs_state.in_([LearningProgress.STATE_LEARNING, LearningProgress.STATE_RELEARNING]))
    if status == 'mastered':
        return query.filter(LearningProgress.fsrs_stability >= 21.0)
    if status == 'hard':
        return query.filter(LearningProgress.fsrs_difficulty >= 8.0)
    
    # Needs Review: Due time passed OR Learning state
    if status == 'needs_review':
        now = datetime.utcnow()
        return query.filter(
            LearningProgress.fsrs_due.isnot(None),
            LearningProgress.fsrs_due <= now,
        )

    if status == 'due_soon':
        now = datetime.utcnow()
        return query.filter(
            LearningProgress.fsrs_due.isnot(None),
            LearningProgress.fsrs_due <= now + timedelta(days=1),
        )

    return query


def paginate_flashcard_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of FlashcardProgress
    page, per_page = sanitize_pagination_args(page, per_page)
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
        
        # Calculate status string for UI display
        state = row.fsrs_state
        stability = row.fsrs_stability or 0
        difficulty = row.fsrs_difficulty or 0
        
        if state == 0:
            status_str = 'new'
        elif state == 1 or state == 3:
            status_str = 'learning'
        elif difficulty >= 8.0:
            status_str = 'hard'
        elif stability >= 21.0:
            status_str = 'mastered'
        else:
            status_str = 'reviewing'

        records.append({
            'container_id': row.container_id,
            'container_title': row.container_title,
            'item_id': row.item_id,
            'front': content.get('front'),
            'back': content.get('back'),
            'status': status_str,
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
            LearningProgress.fsrs_state.label('fsrs_state'),
            LearningProgress.fsrs_stability.label('fsrs_stability'),
            LearningProgress.fsrs_difficulty.label('fsrs_difficulty'),
            LearningProgress.fsrs_last_review.label('last_reviewed'),
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
    # MIGRATED: Use FSRS Logic
    if not status or status == 'all':
        return query

    status = status.lower()
    
    if status == 'new':
        return query.filter(LearningProgress.fsrs_state == LearningProgress.STATE_NEW)
    if status == 'learning':
        return query.filter(LearningProgress.fsrs_state.in_([LearningProgress.STATE_LEARNING, LearningProgress.STATE_RELEARNING]))
    if status == 'mastered':
        return query.filter(LearningProgress.fsrs_stability >= 5.0) # Lower threshold for Quiz?
    if status == 'hard':
        return query.filter(LearningProgress.fsrs_difficulty >= 8.0)

    if status == 'needs_review':
        # Custom logic for Quiz needs review?
        # Maybe incorrect ratio?
        return query.filter(
            or_(
                LearningProgress.fsrs_state.in_([LearningProgress.STATE_LEARNING, LearningProgress.STATE_RELEARNING]),
                LearningProgress.times_incorrect > LearningProgress.times_correct,
            )
        )

    return query


def paginate_quiz_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of QuizProgress
    page, per_page = sanitize_pagination_args(page, per_page)
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
            'status': 'new' if row.fsrs_state == 0 else ('learning' if row.fsrs_state in [1,3] else 'reviewing'),
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
            LearningProgress.legacy_mastery.label('mastery'),  # Mapped to legacy_mastery
            LearningProgress.fsrs_last_review.label('last_updated'),
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
    # mastery >= 1.0 means 100% complete
    if not status or status == 'all':
        return query

    status = status.lower()
    if status == 'completed':
        return query.filter(LearningProgress.legacy_mastery >= 1.0)
    if status == 'in_progress':
        return query.filter(
            LearningProgress.legacy_mastery > 0,
            LearningProgress.legacy_mastery < 1.0,
        )
    if status == 'not_started':
        return query.filter(LearningProgress.legacy_mastery == 0)

    return query


def paginate_course_items(user_id, container_id=None, status=None, page=1, per_page=10):
    # MIGRATED: Use LearningProgress instead of CourseProgress
    page, per_page = sanitize_pagination_args(page, per_page)
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


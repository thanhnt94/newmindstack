# File: mindstack_app/modules/stats/services/metrics.py
# Phiên bản: 3.0 (Refactored for ItemMemoryState)

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
# REFAC: ItemMemoryState removed
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService

# Import pure logic from chart_utils
from ..logics.chart_utils import (
    resolve_timeframe_dates,
    normalize_datetime_range,
    date_range,
    parse_history_datetime,
    sanitize_pagination,
)


ITEM_TYPE_LABELS = {
    'FLASHCARD': 'Flashcard',
    'QUIZ_MCQ': 'Trắc nghiệm',
    'LESSON': 'Bài học',
    'COURSE': 'Khoá học',
}

def get_user_container_options(user_id, container_type, learning_mode, timestamp_attr='last_review', item_type=None):
    """Return the list of learning containers (id/title) a user interacted with."""
    
    # REFAC: Use LearningHistoryInterface
    from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
    
    results = LearningHistoryInterface.get_recent_containers(
        user_id=user_id,
        container_type=container_type,
        item_type=item_type
    )
    
    return [
        {
            'id': row['id'],
            'title': row['title'],
        }
        for row in results
    ]


def sanitize_pagination_args(page, per_page, default_per_page=10, max_per_page=50):
    """Normalise pagination parameters coming from query strings."""
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    if page < 1: page = 1
    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = default_per_page
    if per_page < 1: per_page = default_per_page
    per_page = min(per_page, max_per_page)
    return page, per_page


def _resolve_timeframe_dates(timeframe):
    """Return (start_date, end_date) for the requested timeframe."""
    end_date = date.today()
    timeframe = (timeframe or '').lower()
    mapping = {'7d': 7, '14d': 14, '30d': 30, '90d': 90, '180d': 180, '365d': 365}
    if timeframe == 'all': return None, end_date
    days = mapping.get(timeframe, 30)
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _normalize_datetime_range(start_date, end_date):
    """Return aware datetime boundaries for filtering timestamps."""
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    else: start_dt = None
    if end_date:
        end_dt = (datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc))
    else: end_dt = None
    return start_dt, end_dt


def _parse_history_datetime(raw_value):
    """Safely parse ISO formatted timestamps stored in JSON histories."""
    if not raw_value: return None
    if isinstance(raw_value, datetime): dt_value = raw_value
    elif isinstance(raw_value, str):
        try:
            normalized = raw_value.replace('Z', '+00:00')
            dt_value = datetime.fromisoformat(normalized)
        except ValueError: return None
    else: return None
    if dt_value.tzinfo is None: dt_value = dt_value.replace(tzinfo=timezone.utc)
    else: dt_value = dt_value.astimezone(timezone.utc)
    return dt_value


def _date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def get_score_trend_series(user_id, timeframe='30d'):
    """Return daily score aggregates for the requested timeframe. Uses ScoreLog (unchanged)."""
    start_date, end_date = _resolve_timeframe_dates(timeframe)
    if end_date is None: end_date = date.today()

    if start_date is None:
        earliest_date = (
            db.session.query(func.min(func.date(ScoreLog.timestamp)))
            .filter(ScoreLog.user_id == user_id)
            .scalar()
        )
        if earliest_date is None:
            return {'timeframe': timeframe, 'series': [], 'total_score': 0, 'average_daily_score': 0}
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
        return {'timeframe': timeframe, 'series': [], 'total_score': 0, 'average_daily_score': 0}

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
    return {'timeframe': timeframe, 'series': series, 'total_score': total_score, 'average_daily_score': average_daily_score}


def get_activity_breakdown(user_id, timeframe='30d'):
    """Aggregate score entries by item type. Uses ScoreLog (unchanged)."""
    start_date, end_date = _resolve_timeframe_dates(timeframe)
    if end_date is None: end_date = date.today()

    if start_date is None:
        earliest_date = (db.session.query(func.min(func.date(ScoreLog.timestamp))).filter(ScoreLog.user_id == user_id).scalar())
        if earliest_date is None:
            return {'timeframe': timeframe, 'total_entries': 0, 'total_score': 0, 'average_score_per_entry': 0, 'buckets': []}
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

    return {'timeframe': timeframe, 'total_entries': total_entries, 'total_score': total_score, 'average_score_per_entry': average_score_per_entry, 'buckets': buckets}


def paginate_flashcard_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = sanitize_pagination_args(page, per_page)
    
    # 1. Fetch Items query (Core Domain)
    query = LearningItem.query.filter(
        LearningItem.item_type == 'FLASHCARD'
    )
    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)
        
    items_list = query.all()
    item_ids = [item.item_id for item in items_list]
    
    # 2. Fetch FSRS States (FSRS Domain)
    # We fetch ALL states for these items to support filtering/sorting in memory
    memory_states = FsrsService.get_memory_states(user_id, item_ids)
    
    # 3. Merge Data
    merged_rows = []
    from datetime import datetime
    now = datetime.now(timezone.utc)
    
    for item in items_list:
        state = memory_states.get(item.item_id)
        
        # Determine status
        fsrs_state = state.state if state else 0
        fsrs_stability = state.stability if state else 0.0
        fsrs_difficulty = state.difficulty if state else 0.0
        due_date = state.due_date if state else None
        last_review = state.last_review if state else None
        created_at = state.created_at if state else None # Assuming we want to sort by created if new
        
        status_str = 'reviewing' # default
        if fsrs_state == 0: status_str = 'new'
        elif fsrs_state == 1 or fsrs_state == 3: status_str = 'learning'
        elif fsrs_difficulty >= 8.0: status_str = 'hard'
        elif fsrs_stability >= 21.0: status_str = 'mastered'
        
        # Apply Filters
        if status and status != 'all':
            s = status.lower()
            if s == 'new' and status_str != 'new': continue
            if s == 'learning' and status_str != 'learning': continue
            if s == 'mastered' and status_str != 'mastered': continue
            if s == 'hard' and status_str != 'hard': continue
            if s == 'needs_review':
                if not (due_date and due_date <= now): continue
            if s == 'due_soon':
                if not (due_date and due_date <= now + timedelta(days=1)): continue
                
        merged_rows.append({
            'item_obj': item,
            'state_obj': state,
            'status': status_str,
            'sort_key': last_review or created_at or datetime.min.replace(tzinfo=timezone.utc)
        })
        
    # 4. Sort
    # Original sort: coalesce(last_review, created_at) desc
    merged_rows.sort(key=lambda x: x['sort_key'], reverse=True)
    
    # 5. Paginate
    total = len(merged_rows)
    start = (page - 1) * per_page
    end = start + per_page
    if start >= total:
        paginated_rows = []
    else:
        paginated_rows = merged_rows[start:end]
        
    # 6. Format Output
    records = []
    for row in paginated_rows:
        item = row['item_obj']
        state = row['state_obj']
        content = item.content or {}
        
        records.append({
            'container_id': item.container_id,
            'container_title': item.container.title if item.container else "", # lazy load container
            'item_id': item.item_id,
            'front': content.get('front'),
            'back': content.get('back'),
            'status': row['status'],
            'last_reviewed': state.last_review.isoformat() if state and state.last_review else None,
            'first_seen': state.created_at.isoformat() if state and state.created_at else None,
            'due_time': state.due_date.isoformat() if state and state.due_date else None,
        })

    return {'status': status or 'all', 'page': page, 'per_page': per_page, 'total': total, 'records': records}


def paginate_quiz_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = sanitize_pagination_args(page, per_page)
    
    # 1. Fetch Items query
    query = LearningItem.query.filter(LearningItem.item_type == 'QUIZ_MCQ')
    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)
        
    items_list = query.all()
    item_ids = [item.item_id for item in items_list]
    
    # 2. Fetch States
    memory_states = FsrsService.get_memory_states(user_id, item_ids)
    
    # 3. Merge
    merged_rows = []
    from datetime import datetime
    
    for item in items_list:
        state = memory_states.get(item.item_id)
        
        fsrs_state = state.state if state else 0
        fsrs_stability = state.stability if state else 0.0
        fsrs_difficulty = state.difficulty if state else 0.0
        times_correct = state.times_correct if state else 0
        times_incorrect = state.times_incorrect if state else 0
        
        status_str = 'reviewing'
        if fsrs_state == 0: status_str = 'new'
        elif fsrs_state == 1 or fsrs_state == 3: status_str = 'learning'
        elif fsrs_stability >= 5.0: status_str = 'mastered'
        elif fsrs_difficulty >= 8.0: status_str = 'hard'
        
        if status and status != 'all':
            s = status.lower()
            if s == 'new' and status_str != 'new': continue
            if s == 'learning' and status_str != 'learning': continue
            if s == 'mastered' and status_str != 'mastered': continue
            if s == 'hard' and status_str != 'hard': continue
            if s == 'needs_review':
                # Custom logic for quiz review: learning OR wrong > right
                is_needs_review = (fsrs_state in [1, 3]) or (times_incorrect > times_correct)
                if not is_needs_review: continue
        
        merged_rows.append({
            'item_obj': item,
            'state_obj': state,
            'status': status_str,
            'sort_key': (state.last_review if state else None) or (state.created_at if state else None) or datetime.min.replace(tzinfo=timezone.utc)
        })
        
    # 4. Sort
    merged_rows.sort(key=lambda x: x['sort_key'], reverse=True)
    
    # 5. Paginate
    total = len(merged_rows)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_rows = merged_rows[start:end] if start < total else []
    
    # 6. Format
    records = []
    for row in paginated_rows:
        item = row['item_obj']
        state = row['state_obj']
        content = item.content or {}
        
        records.append({
            'container_id': item.container_id,
            'container_title': item.container.title if item.container else "",
            'item_id': item.item_id,
            'question': content.get('question'),
            'status': row['status'],
            'times_correct': int((state.times_correct if state else 0)),
            'times_incorrect': int((state.times_incorrect if state else 0)),
            'last_reviewed': state.last_review.isoformat() if state and state.last_review else None,
            'first_seen': state.created_at.isoformat() if state and state.created_at else None,
        })

    return {'status': status or 'all', 'page': page, 'per_page': per_page, 'total': total, 'records': records}


def paginate_course_items(user_id, container_id=None, status=None, page=1, per_page=10):
    page, per_page = sanitize_pagination_args(page, per_page)
    
    # 1. Fetch Items
    query = LearningItem.query.filter(LearningItem.item_type == 'LESSON')
    if container_id is not None:
        query = query.filter(LearningItem.container_id == container_id)
        
    items_list = query.all()
    item_ids = [item.item_id for item in items_list]
    
    # 2. Fetch States
    memory_states = FsrsService.get_memory_states(user_id, item_ids)
    
    # 3. Merge
    merged_rows = []
    for item in items_list:
        state = memory_states.get(item.item_id)
        
        data = (state.data or {}) if state else {}
        completion_pct = int(data.get('completion_percentage', 0))
        
        status_str = 'not_started'
        if completion_pct >= 100: status_str = 'completed'
        elif completion_pct > 0: status_str = 'in_progress'
        
        if status and status != 'all':
            s = status.lower()
            if s == 'completed' and status_str != 'completed': continue
            if s == 'in_progress' and status_str != 'in_progress': continue
            if s == 'not_started' and status_str != 'not_started': continue
            
        merged_rows.append({
            'item_obj': item,
            'state_obj': state,
            'status': status_str,
            'completion_pct': completion_pct,
            'sort_key': (state.last_review if state else None) or (state.created_at if state else None) or datetime.min.replace(tzinfo=timezone.utc)
        })
        
    # 4. Sort
    merged_rows.sort(key=lambda x: x['sort_key'], reverse=True)
    
    # 5. Paginate
    total = len(merged_rows)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_rows = merged_rows[start:end] if start < total else []
    
    # 6. Format
    records = []
    for row in paginated_rows:
        item = row['item_obj']
        state = row['state_obj']
        content = item.content or {}
        
        records.append({
            'container_id': item.container_id,
            'container_title': item.container.title if item.container else "",
            'item_id': item.item_id,
            'title': content.get('title') or content.get('lesson_title'),
            'status': row['status'],
            'completion_percentage': row['completion_pct'],
            'last_updated': state.last_review.isoformat() if state and state.last_review else None,
        })

    return {'status': status or 'all', 'page': page, 'per_page': per_page, 'total': int(total), 'records': records}


def get_flashcard_activity_series(user_id, container_id, timeframe='30d'):
    # MIGRATED: Use LearningHistoryInterface
    if not container_id: return {'series': []}
    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    
    from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
    
    logs = LearningHistoryInterface.get_daily_activity_series(
        user_id, timeframe_start, timeframe_end, container_id, 'FLASHCARD'
    )
    
    new_counts = defaultdict(int)
    review_counts = defaultdict(int)
    
    for (ts, mode) in logs:
        # Simplification to reviews
        dt_val = ts
        if not dt_val: continue
        entry_date = dt_val.date()
        review_counts[entry_date] += 1
        
    # Calculate score from ScoreLog as before
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

    return {'series': series, 'start_date': timeframe_start.isoformat(), 'end_date': timeframe_end.isoformat(), 'timeframe': timeframe or '30d'}


# Reuse get_flashcard_activity_series logic for quiz (simplified)
def get_quiz_activity_series(user_id, container_id, timeframe='30d'):
    # MIGRATED: Use LearningHistoryInterface
    if not container_id: return {'series': []}
    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)
    
    from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
    
    logs = LearningHistoryInterface.get_daily_activity_series(
        user_id, timeframe_start, timeframe_end, container_id, 'QUIZ_MCQ'
    )
    
    review_counts = defaultdict(int)
    for (ts, mode) in logs:
        if ts: review_counts[ts.date()] += 1
        
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
            'new_count': 0,
            'review_count': int(review_counts.get(current_date, 0)),
            'score': int(score_map.get(current_date, 0)),
        })

    return {'series': series, 'start_date': timeframe_start.isoformat(), 'end_date': timeframe_end.isoformat(), 'timeframe': timeframe or '30d'}


def get_course_activity_series(user_id, container_id, timeframe='30d'):
    # REFAC: Use FsrsInterface
    if not container_id: return {'series': []}
    timeframe_start, timeframe_end = _resolve_timeframe_dates(timeframe)

    # 1. Fetch Items
    items = db.session.query(LearningItem.item_id).filter(
        LearningItem.container_id == container_id,
        LearningItem.item_type == 'LESSON'
    ).all()
    item_ids = [r.item_id for r in items]
    
    # 2. Fetch States
    states = FsrsService.get_memory_states(user_id, item_ids)
    
    new_counts = defaultdict(int)
    review_counts = defaultdict(int)

    for iid, state in states.items():
        last_updated = state.last_review
        if not last_updated: continue
        
        entry_date = last_updated.date()
        if timeframe_start and entry_date < timeframe_start: continue
        if timeframe_end and entry_date > timeframe_end: continue

        data_dict = (state.data or {}) if state.data else {}
        completion_percentage = data_dict.get('completion_percentage', 0)
        
        if completion_percentage > 0: new_counts[entry_date] += 1
        if completion_percentage >= 100: review_counts[entry_date] += 1

    series = []
    for current_date in _date_range(timeframe_start, timeframe_end):
        series.append({
            'date': current_date.isoformat(),
            'new_count': int(new_counts.get(current_date, 0)),
            'review_count': int(review_counts.get(current_date, 0)),
            'score': 0,
        })

    return {'series': series, 'start_date': timeframe_start.isoformat(), 'end_date': timeframe_end.isoformat(), 'timeframe': timeframe or '30d'}


def get_flashcard_set_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate flashcard metrics per set for the provided user."""
    # 1. Fetch Containers
    container_query = (
        db.session.query(LearningContainer.container_id, LearningContainer.title)
        .filter(LearningContainer.container_type == 'FLASHCARD_SET')
    )
    if container_id is not None:
        container_query = container_query.filter(LearningContainer.container_id == container_id)
        
    containers = container_query.all()
    if not containers: return {}
    
    container_map = {c.container_id: c.title for c in containers}
    container_ids = list(container_map.keys())
    
    # 2. Fetch Items for these containers
    items_query = (
        db.session.query(LearningItem.item_id, LearningItem.container_id)
        .filter(
            LearningItem.item_type == 'FLASHCARD',
            LearningItem.container_id.in_(container_ids)
        )
    )
    items = items_query.all()
    
    # Map container_id -> list of item_ids
    container_items_map = defaultdict(list)
    all_item_ids = []
    for iid, cid in items:
        container_items_map[cid].append(iid)
        all_item_ids.append(iid)
        
    # 3. Fetch FSRS States
    memory_states = FsrsService.get_memory_states(user_id, all_item_ids)
    
    # 4. Aggregate
    result = {}
    
    for cid in container_ids:
        c_items = container_items_map[cid]
        total_cards = len(c_items)
        
        studied_cards = 0
        learned_cards = 0
        total_correct = 0
        total_incorrect = 0
        sum_streak = 0
        best_streak = 0
        count_with_streak = 0
        
        for iid in c_items:
            state = memory_states.get(iid)
            if state:
                studied_cards += 1
                if (state.stability or 0) >= 21.0:
                    learned_cards += 1
                
                total_correct += (state.times_correct or 0)
                total_incorrect += (state.times_incorrect or 0)
                
                streak = state.streak or 0
                if streak > 0:
                    sum_streak += streak
                    count_with_streak += 1
                if streak > best_streak:
                    best_streak = streak
        
        total_attempts = total_correct + total_incorrect
        accuracy_percent = round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else None
        avg_streak = (sum_streak / count_with_streak) if count_with_streak > 0 else 0.0
        
        # Paginate Items for 'items' key (using our refactored function)
        # Note: This calls paginate again, which does another fetch. 
        # Optimization: We could reuse data, but `paginate` function is cleaner to call separately unless perf is critical.
        # Given we are calling this for potentially specific container_id (Detailed view), it's fine.
        # IF calling for ALL containers (Dashboard), we usually don't need 'items' list inside.
        # IMPORTANT: The UI logic might expect 'items' payload map.
        # The original code did: `items_payload_map[target_id] = paginate...`
        # It only paginated if `container_id` was specific (or iteration logic).
        # Original: `target_ids = container_ids if container_id is None else [container_id]` -> Wait.
        # Original: `items_payload_map = {} ... for target_id in target_ids: ...`
        # This means it paginates for ALL containers if container_id is None. That's heavy.
        # But if the UI requests it...
        
        items_payload = {'status': status or 'all', 'page': page, 'per_page': per_page, 'total': 0, 'records': []}
        # Only fetch items if we are looking at a specific container or if list is small?
        # The original code strictly did it. I will keep behavior.
        items_payload = paginate_flashcard_items(user_id, container_id=cid, status=status, page=page, per_page=per_page)
        
        result[cid] = {
            'container_id': cid, 'container_title': container_map[cid],
            'total_cards': total_cards, 'studied_cards': studied_cards, 'learned_cards': learned_cards,
            'accuracy_percent': accuracy_percent, 'avg_correct_streak': round(avg_streak, 1), 'best_correct_streak': best_streak,
            'items': items_payload
        }
        
    return result


def get_quiz_set_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate quiz metrics per set."""
    # 1. Fetch Containers
    container_query = (
        db.session.query(LearningContainer.container_id, LearningContainer.title)
        .filter(LearningContainer.container_type == 'QUIZ_SET')
    )
    if container_id is not None:
        container_query = container_query.filter(LearningContainer.container_id == container_id)
        
    containers = container_query.all()
    if not containers: return {}
    
    container_map = {c.container_id: c.title for c in containers}
    container_ids = list(container_map.keys())
    
    # 2. Fetch Items
    items_query = (
        db.session.query(LearningItem.item_id, LearningItem.container_id)
        .filter(
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningItem.container_id.in_(container_ids)
        )
    )
    items = items_query.all()
    
    container_items_map = defaultdict(list)
    all_item_ids = []
    for iid, cid in items:
        container_items_map[cid].append(iid)
        all_item_ids.append(iid)
        
    # 3. Fetch States
    memory_states = FsrsService.get_memory_states(user_id, all_item_ids)
    
    # 4. Aggregate
    # 4. Aggregate via FSRS Interface
    # REFAC: Use FsrsInterface
    stats_map = FsrsService.get_detailed_container_stats(user_id, container_ids, item_type='QUIZ_MCQ')
    
    result = {}
    for container_id in container_ids:
        progress = stats_map.get(container_id, {})
        total_items = len(container_items_map[container_id])
        
        # Calculate derived stats
        total_correct = progress.get('correct', 0)
        total_incorrect = progress.get('incorrect', 0)
        total_attempts = total_correct + total_incorrect
        accuracy_percent = round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else 0.0
        
        items_payload = paginate_quiz_items(user_id, container_id=container_id, status=status, page=page, per_page=per_page)
        
        result[container_id] = {
            'container_id': container_id, 'container_title': container_map.get(container_id, ""),
            'total_questions': total_items,
            'attempted_questions': progress.get('attempted', 0),
            'total_correct': total_correct, 
            'total_incorrect': total_incorrect,
            'accuracy_percent': accuracy_percent,
            'avg_correct_streak': round(progress.get('avg_streak', 0.0), 1),
            'best_correct_streak': progress.get('best_streak', 0),
            'items': items_payload
        }
    
    return result


def get_course_metrics(user_id, container_id=None, status=None, page=1, per_page=10):
    """Aggregate course metrics."""
    # REFAC: Use FsrsInterface
    # Original logic only showed ACTIVE courses (joined ItemMemoryState).
    # So we fetch stats first (which implies activity), then fetch headers.
    
    # 1. Get stats for active courses (or specific one)
    target_ids = [container_id] if container_id else None
    stats_map = FsrsService.get_course_container_stats(user_id, target_ids)
    
    active_container_ids = list(stats_map.keys())
    if not active_container_ids:
        return {}
        
    # 2. Fetch Container Titles for active ones
    containers = (
        db.session.query(LearningContainer.container_id, LearningContainer.title)
        .filter(LearningContainer.container_id.in_(active_container_ids))
        .all()
    )
    title_map = {c.container_id: c.title for c in containers}
    
    # 3. Fetch Total Lessons for active ones
    total_lessons_map = dict(
        db.session.query(LearningItem.container_id, func.count(LearningItem.item_id).label('total_lessons'))
        .filter(LearningItem.item_type == 'LESSON', LearningItem.container_id.in_(active_container_ids))
        .group_by(LearningItem.container_id).all()
    )

    result = {}
    for cid in active_container_ids:
        progress = stats_map.get(cid, {})
        total_lessons = int(total_lessons_map.get(cid, 0) or 0)
        
        items_payload = paginate_course_items(user_id, container_id=cid, status=status, page=page, per_page=per_page)

        result[cid] = {
            'container_id': cid, 'container_title': title_map.get(cid, ""),
            'total_lessons': total_lessons, 
            'lessons_started': progress.get('started', 0),
            'lessons_completed': progress.get('completed', 0), 
            'avg_completion_percent': round(progress.get('avg_completion', 0.0), 1),
            'last_activity': progress.get('last_activity').isoformat() if progress.get('last_activity') else None,
            'items': items_payload
        }
    return result
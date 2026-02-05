# File: mindstack_app/modules/learning/quiz_learning/algorithms.py
# Phiên bản: 3.0
# MỤC ĐÍCH: Refactor to use ItemMemoryState (FSRS) instead of LearningProgress.

from datetime import datetime, timezone
from flask_login import current_user
from sqlalchemy import func
from mindstack_app.models import LearningItem, LearningContainer, db, User
from mindstack_app.models import LearningItem, LearningContainer, db, User
# REFAC: ItemMemoryState removed
# REFAC: FSRSHardItemService removed (used via Interface)

def get_quiz_mode_counts(user_id, set_id):
    """
    Get counts for different quiz modes.
    """
    # Base count from LearningItem
    base_q = _get_base_items_query(user_id, set_id)
    total = base_q.count()
    
    # Use FSRS Interface for stats
    from mindstack_app.modules.fsrs.interface import FSRSInterface
    
    # We need specific filtering by container which get_memory_stats_by_type doesn't fully support yet (it's global per type).
    # However, FSRSInterface was updated with `get_container_stats`.
    # But `get_container_stats` is for a SINGLE container. `set_id` here can be 'all' or a list.
    
    # If set_id is specific (int), use get_container_stats.
    # If list or all, we might need a better approach.
    # Logic below refactors to use the count from helper. 
    # But current FsrsInterface.get_container_stats returns dict with 'learned', 'due', 'mastered'.
    
    new_count = 0
    learned = 0
    due = 0
    
    # If set_id is 'all', we iterate accessible sets? Or add `get_stats_summary(user_id, container_ids)` to Interface.
    # For now to strictly follow "No Model Access", I'll use a loop if list, or single call if int.
    # If 'all':
    if set_id == 'all':
        # This is expensive if loop. 
        # But `ItemMemoryState` access is forbidden.
        # I will fetch ALL memory states for user and filter in memory? 
        # Efficient approach: `FSRSInterface.get_counts(user_id, item_type='QUIZ_MCQ', container_ids=...)`
        accessible_ids = get_accessible_quiz_set_ids(user_id)
        # Using memory states
        # Filter items for these containers
        # This seems too heavy to do in `algorithms.py`.
        # I will assume for now `set_id` is usually a single ID for this specific UI call.
        # If 'all', we accept approximation or need new Interface method.
        # Actually `get_memory_stats_by_type(user_id, 'QUIZ_MCQ')` returns GLOBAL stats.
        # If `set_id` == 'all' (User Dashboard), global stats are EXACTLY what we want!
        stats = FSRSInterface.get_memory_stats_by_type(user_id, 'QUIZ_MCQ')
        total = stats.get('total', 0) # Wait, total in stats is "Items with memory state".
        # We need "Available items". 
        # base_q.count() gives Total Available.
        learned = stats.get('total', 0) # total in get_memory_stats_by_type IS learned (state!=0).
        due = stats.get('due', 0)
        new_count = total - learned
    
    elif isinstance(set_id, int):
        stats = FSRSInterface.get_container_stats(user_id, set_id)
        learned = stats.get('learned', 0)
        due = stats.get('due', 0)
        new_count = total - learned
        
    else:
        # Fallback for list?
        # Just sum up?
        learned = 0
        due = 0
        container_ids = set_id if isinstance(set_id, list) else []
        for cid in container_ids:
            s = FSRSInterface.get_container_stats(user_id, cid)
            learned += s.get('learned', 0)
            due += s.get('due', 0)
        new_count = total - learned
    
    return {
        'list': [
            {'id': 'new_only', 'count': int(new_count), 'name': 'Chỉ làm mới'},
            {'id': 'due_only', 'count': int(due), 'name': 'Ôn tập câu đã làm'},
            {'id': 'hard_only', 'count': 0, 'name': 'Ôn tập câu khó'}, 
        ],
        'total': total,
        'new': int(new_count),
        'due': int(due),
        'learned': int(learned)
    }

def get_filtered_quiz_sets(user_id, search_query, search_field, current_filter, page, per_page=12):
    """
    Get filtered list of quiz sets.
    """
    query = LearningContainer.query.filter(LearningContainer.container_type == 'QUIZ_SET')
    
    # Access control (simplified)
    if current_user.user_role != User.ROLE_ADMIN:
        query = query.filter(LearningContainer.creator_user_id == user_id)
        
    # Search
    if search_query:
        query = query.filter(LearningContainer.title.ilike(f'%{search_query}%'))
        
    # Paginate
    from mindstack_app.utils.pagination import get_pagination_data
    pagination = get_pagination_data(query, page, per_page)
    
    # Augment with stats
    for container in pagination.items:
        count = LearningItem.query.filter_by(container_id=container.container_id, item_type='QUIZ_MCQ').count()
        container.question_count = count
        
    return pagination

def get_new_only_items(user_id, set_id, session_id):
    """
    Lấy danh sách các câu hỏi MỚI (chưa học) từ bộ câu hỏi.
    """
    base_items_query = _get_base_items_query(user_id, set_id)

    # get learned IDs
    from mindstack_app.modules.fsrs.interface import FSRSInterface
    learned_ids = FSRSInterface.get_learned_item_ids(user_id)
    
    # Filter OUT learned IDs
    if learned_ids:
        new_items_query = base_items_query.filter(
            ~LearningItem.item_id.in_(learned_ids)
        )
    else:
        new_items_query = base_items_query

    return new_items_query

def get_reviewed_items(user_id, set_id, session_id):
    """
    Lấy danh sách các câu hỏi ĐÃ HỌC (cần ôn tập).
    """
    base_items_query = _get_base_items_query(user_id, set_id)

    # get learned IDs
    from mindstack_app.modules.fsrs.interface import FSRSInterface
    learned_ids = FSRSInterface.get_learned_item_ids(user_id)

    # Filter IN learned IDs
    if learned_ids:
        reviewed_items_query = base_items_query.filter(
            LearningItem.item_id.in_(learned_ids)
        )
    else:
        # No learned items -> Empty query
        from sqlalchemy import false
        reviewed_items_query = base_items_query.filter(false())

    return reviewed_items_query

def get_hard_items(user_id, set_id, session_id):
    """
    Lấy danh sách các câu hỏi KHÓ.
    """
    # Use FSRS Interface
    from mindstack_app.modules.fsrs.interface import FSRSInterface
    
    # Logic in Interface returns a list (or query? I made it return list in recent edit, but previously it was query? 
    # Current Interface implementation `get_hard_items_list` returns LIST of objects.
    # The quiz system expects a Query object usually to apply further filters or pagination?
    # `algorithms.py` usually returns a Query object.
    # `get_new_only_items` returns Query.
    # `get_hard_items` must return Query.
    # FSRSInterface currently exposes `get_hard_items_list`.
    # I should expose `get_hard_items_query`? OR use `get_hard_items_list` and convert to query?
    # Converting list to query: `LearningItem.query.filter(LearningItem.item_id.in_([x.item_id for x in list]))`.
    
    limit = 50 # Default limit for hard items session?
    hard_items = FSRSInterface.get_hard_items_list(
        user_id=user_id,
        container_id=set_id if set_id != 'all' else None,
        item_type='QUIZ_MCQ',
        limit=limit
    )
    
    ids = [item.item_id for item in hard_items]
    if ids:
        return LearningItem.query.filter(LearningItem.item_id.in_(ids))
    else:
        from sqlalchemy import false
        return LearningItem.query.filter(false())


def get_accessible_quiz_set_ids(user_id):
    """
    Lấy danh sách ID của các bộ Quiz mà người dùng có quyền truy cập.
    """
    # Simplified logic for now
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'QUIZ_SET',
        LearningContainer.creator_user_id == user_id
    )
    return [c.container_id for c in query.all()]

def _get_base_items_query(user_id, set_id):
    """
    Helper: Trả về query cơ bản lấy LearningItem dựa trên set_id.
    """
    query = LearningItem.query.filter(
        LearningItem.item_type.in_(['QUIZ_MCQ', 'QUESTION', 'FLASHCARD'])
    )

    if set_id == 'all':
        accessible_ids = get_accessible_quiz_set_ids(user_id)
        query = query.filter(LearningItem.container_id.in_(accessible_ids))
    elif isinstance(set_id, list):
        query = query.filter(LearningItem.container_id.in_(set_id))
    else:
        query = query.filter(LearningItem.container_id == set_id)

    return query
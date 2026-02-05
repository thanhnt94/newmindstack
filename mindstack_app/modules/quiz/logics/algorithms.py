# File: mindstack_app/modules/learning/quiz_learning/algorithms.py
# Phiên bản: 3.0
# MỤC ĐÍCH: Refactor to use ItemMemoryState (FSRS) instead of LearningProgress.

from datetime import datetime, timezone
from flask_login import current_user
from sqlalchemy import func
from mindstack_app.models import LearningItem, LearningContainer, db, User
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.services.hard_item_service import FSRSHardItemService

def get_quiz_mode_counts(user_id, set_id):
    """
    Get counts for different quiz modes.
    """
    base_q = _get_base_items_query(user_id, set_id)
    total = base_q.count()
    
    now = datetime.now(datetime.timezone.utc) if hasattr(datetime, 'timezone') else datetime.utcnow()
    
    # Learned (state != 0)
    learned_q = base_q.join(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
        ItemMemoryState.state != 0
    )
    learned = learned_q.count()
    
    new_count = total - learned
    
    # Due
    due_q = base_q.join(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
        ItemMemoryState.state != 0,
        ItemMemoryState.due_date <= now
    )
    due = due_q.count()
    
    return {
        'list': [
            {'id': 'new_only', 'count': new_count, 'name': 'Chỉ làm mới'},
            {'id': 'due_only', 'count': due, 'name': 'Ôn tập câu đã làm'},
            {'id': 'hard_only', 'count': 0, 'name': 'Ôn tập câu khó'}, # Hard count logic omitted
        ],
        'total': total,
        'new': new_count,
        'due': due,
        'learned': learned
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

    # Query new items using ItemMemoryState (state=0 or NULL)
    new_items_query = base_items_query.outerjoin(ItemMemoryState,
        (ItemMemoryState.item_id == LearningItem.item_id) &
        (ItemMemoryState.user_id == user_id)
    ).filter(
        (ItemMemoryState.state == None) | (ItemMemoryState.state == 0)
    )

    return new_items_query

def get_reviewed_items(user_id, set_id, session_id):
    """
    Lấy danh sách các câu hỏi ĐÃ HỌC (cần ôn tập).
    """
    base_items_query = _get_base_items_query(user_id, set_id)

    # Query reviewed items using ItemMemoryState
    reviewed_items_query = base_items_query.join(
        ItemMemoryState,
        (ItemMemoryState.item_id == LearningItem.item_id) &
        (ItemMemoryState.user_id == user_id)
    ).filter(
        ItemMemoryState.state != 0
    )

    return reviewed_items_query

def get_hard_items(user_id, set_id, session_id):
    """
    Lấy danh sách các câu hỏi KHÓ.
    """
    # Use centralized service query
    query = FSRSHardItemService.get_hard_items_query(
        user_id=user_id,
        container_id=set_id if set_id != 'all' else None,
        learning_mode='quiz'
    )
    
    # Filter for Quiz items specifically
    query = query.filter(LearningItem.item_type == 'QUIZ_MCQ')
    
    return query

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
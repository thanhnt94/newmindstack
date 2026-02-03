# File: flashcard/engine/algorithms.py
# Flashcard Algorithms - High level algorithms for set selection and mode counts.

from mindstack_app.models import LearningContainer, LearningItem, User, ContainerContributor, UserContainerState, db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from flask_login import current_user
from sqlalchemy import func, or_, and_, case
from datetime import datetime, timezone

def get_filtered_flashcard_sets(user_id, search_query, search_field, current_filter, page, per_page=12):
    """
    Get filtered list of flashcard sets.
    """
    # Base query
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET'
    )
    
    # Access control
    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        query = query.filter(LearningContainer.creator_user_id == user_id)
    else:
        access_conditions = [
            LearningContainer.creator_user_id == user_id,
            LearningContainer.is_public == True
        ]
        # Contributions
        contributed_ids = db.session.query(ContainerContributor.container_id).filter(
            ContainerContributor.user_id == user_id
        ).all()
        if contributed_ids:
            access_conditions.append(LearningContainer.container_id.in_([c.container_id for c in contributed_ids]))
        query = query.filter(or_(*access_conditions))

    # Search
    if search_query:
        if search_field == 'title':
            query = query.filter(LearningContainer.title.ilike(f'%{search_query}%'))
        else:
            query = query.filter(or_(
                LearningContainer.title.ilike(f'%{search_query}%'),
                LearningContainer.description.ilike(f'%{search_query}%')
            ))

    # Filter tabs
    user_interacted = db.session.query(UserContainerState.container_id).filter(
        UserContainerState.user_id == user_id
    ).subquery()

    if current_filter == 'archive':
        query = query.join(UserContainerState, 
            (UserContainerState.container_id == LearningContainer.container_id) & 
            (UserContainerState.user_id == user_id)
        ).filter(UserContainerState.is_archived == True)
    elif current_filter == 'doing':
        query = query.join(UserContainerState, 
            (UserContainerState.container_id == LearningContainer.container_id) & 
            (UserContainerState.user_id == user_id)
        ).filter(UserContainerState.is_archived == False)
    elif current_filter == 'explore':
        query = query.filter(~LearningContainer.container_id.in_(user_interacted))
    
    # Sort
    query = query.order_by(LearningContainer.created_at.desc())
    
    # Paginate
    from mindstack_app.utils.pagination import get_pagination_data
    pagination = get_pagination_data(query, page, per_page)
    
    # Augment with stats
    for container in pagination.items:
        total_items = LearningItem.query.filter(
            LearningItem.container_id == container.container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()
        
        learned_count = 0
        if total_items > 0:
            learned_count = db.session.query(func.count(ItemMemoryState.state_id)).join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id).filter(
                LearningItem.container_id == container.container_id,
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.state != 0
            ).scalar() or 0
            
        container.total_items = total_items
        container.completion_percentage = (learned_count / total_items * 100) if total_items > 0 else 0
        container.item_count_display = f"{learned_count} / {total_items}"
        
        ucs = UserContainerState.query.filter_by(user_id=user_id, container_id=container.container_id).first()
        container.user_state = ucs.to_dict() if ucs else {'is_archived': False}

    return pagination

def get_flashcard_mode_counts(user_id, set_id, context='vocab'):
    """
    Get counts for different modes (new, due, etc.).
    """
    def _base_item_query(s_id):
        q = LearningItem.query.filter(LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY']))
        if s_id != 'all':
            if isinstance(s_id, list): q = q.filter(LearningItem.container_id.in_(s_id))
            else: q = q.filter(LearningItem.container_id == s_id)
        return q

    base_q = _base_item_query(set_id)
    total = base_q.count()
    learned_q = base_q.join(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
        ItemMemoryState.state != 0
    )
    learned = learned_q.count()
    new_count = total - learned
    
    now = datetime.now(timezone.utc)
    due_q = base_q.join(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
        ItemMemoryState.state != 0,
        ItemMemoryState.due_date <= now
    )
    due = due_q.count()
    
    hard_q = base_q.join(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
        ItemMemoryState.difficulty >= 7.0
    )
    hard = hard_q.count()
    
    from .vocab_flashcard_mode import get_flashcard_modes
    mode_list = []
    registered_modes = get_flashcard_modes(context)
    
    for mode in registered_modes:
        mode_count = 0
        if mode.id == 'new_only': mode_count = new_count
        elif mode.id == 'due_only': mode_count = due
        elif mode.id == 'hard_only': mode_count = hard
        elif mode.id == 'all_review': mode_count = learned
        else: mode_count = new_count + due # mixed, sequential
        
        mode_list.append({
            'id': mode.id,
            'count': mode_count,
            'label': mode.label,
            'icon': mode.icon,
            'color': mode.color,
            'description': mode.description
        })

    return {
        'total': total,
        'new': new_count,
        'due': due,
        'learned': learned,
        'hard': hard,
        'list': mode_list
    }

def get_accessible_flashcard_set_ids(user_id):
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET',
        LearningContainer.creator_user_id == user_id
    )
    return [c.container_id for c in query.all()]

from .services.query_builder import FlashcardQueryBuilder

def get_new_only_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_new_only()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

def get_due_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_due_only()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

def get_reviewed_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_all_review()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

def get_sequential_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_sequential()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

def get_hard_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_hard_only()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

def get_mixed_items(user_id, set_id, limit=None):
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_mixed()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query
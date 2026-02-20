# File: flashcard/engine/algorithms.py
# Flashcard Algorithms - High level algorithms for set selection and mode counts.

from mindstack_app.models import LearningContainer, LearningItem, User, ContainerContributor, UserContainerState, db
# REFAC: Removed ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
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
        
        # REFAC: Use FsrsInterface
        learned_count = 0
        if total_items > 0:
            learned_count = FsrsInterface.get_learned_count(user_id, container.container_id)
            
        container.total_items = total_items
        container.completion_percentage = (learned_count / total_items * 100) if total_items > 0 else 0
        container.item_count_display = f"{learned_count} / {total_items}"
        
        ucs = UserContainerState.query.filter_by(user_id=user_id, container_id=container.container_id).first()
        container.user_state = ucs.to_dict() if ucs else {'is_archived': False}

    return pagination

def get_flashcard_mode_counts(user_id, set_id, context='vocab'):
    """
    Get counts for the unified SRS mode.
    """
    def _base_item_query(s_id):
        q = LearningItem.query.filter(LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY']))
        if s_id != 'all':
            if isinstance(s_id, list): q = q.filter(LearningItem.container_id.in_(s_id))
            else: q = q.filter(LearningItem.container_id == s_id)
        return q

    # Total available (New or Due)
    q_srs = _base_item_query(set_id)
    q_srs = FsrsInterface.apply_memory_filter(q_srs, user_id, 'srs')
    srs_count = q_srs.count()
    
    # Calculate Breakdown
    q_due = _base_item_query(set_id)
    q_due = FsrsInterface.apply_memory_filter(q_due, user_id, 'due')
    due_count = q_due.count()
    
    q_new = _base_item_query(set_id)
    q_new = FsrsInterface.apply_memory_filter(q_new, user_id, 'new')
    new_count = q_new.count()

    from .vocab_flashcard_mode import get_flashcard_modes
    mode_list = []
    registered_modes = get_flashcard_modes(context)
    
    for mode in registered_modes:
        count = 0
        if mode.id in ['srs', 'mixed_srs']:
            count = srs_count
        elif mode.id == 'new':
            count = new_count
        elif mode.id in ['cram', 'review']:
            # Cram/Review Mode: Learned items only
            q_rev = _base_item_query(set_id)
            q_rev = FsrsInterface.apply_memory_filter(q_rev, user_id, 'review')
            count = q_rev.count()
        else:
            # Default to SRS if unknown, or 0? 
            # Let's default to SRS for safety or 0 if strictly separate.
            # Given the UI shows (--), 0 might be safer to indicate "calc required" but here we return final.
            count = srs_count 

        mode_list.append({
            'id': mode.id,
            'count': count,
            'label': mode.label,
            'icon': mode.icon,
            'color': mode.color,
            'description': mode.description
        })

    result = {
        'total': srs_count,
        'srs': srs_count,
        'due': due_count,
        'new': new_count,
        'list': mode_list
    }
    
    # [FIX] Ensure all mode counts are available as top-level keys for template lookup
    for item in mode_list:
        result[item['id']] = item['count']

    return result

def get_accessible_flashcard_set_ids(user_id):
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET',
        LearningContainer.creator_user_id == user_id
    )
    return [c.container_id for c in query.all()]

# Import from services layer (correct location per architecture)
from ..services.query_builder import FlashcardQueryBuilder

def get_srs_items(user_id, set_id, limit=None):
    """Unified SRS item retrieval."""
    qb = FlashcardQueryBuilder(user_id)
    if set_id != 'all': qb.filter_by_containers([set_id] if isinstance(set_id, int) else set_id)
    qb.filter_srs()
    query = qb.get_query()
    if limit: query = query.limit(limit)
    return query

"""
Flashcard Algorithms - Backward Compatibility Facade

This module re-exports functions from the new service classes
to maintain backward compatibility with existing code.

New code should import directly from:
- FlashcardPermissionService (permission_service.py)
- FlashcardQueryBuilder (query_builder.py)
- FlashcardItemService (item_service.py)

File: mindstack_app/modules/learning/flashcard/engine/algorithms.py
Version: 5.0 (Refactored to services)
"""
from flask import current_app
from sqlalchemy import func, and_, or_

from mindstack_app.models import (
    db,
    LearningItem,
    LearningContainer,
    ContainerContributor,
    UserContainerState,
    User,
)
from mindstack_app.modules.learning.models import LearningProgress
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from flask_login import current_user

from .config import FlashcardLearningConfig

# Import new services
from .services import (
    FlashcardPermissionService,
    FlashcardQueryBuilder,
    FlashcardItemService,
)


# =============================================================================
# BACKWARD COMPATIBLE FUNCTION EXPORTS
# =============================================================================
# These delegate to the new service classes to maintain API compatibility

def get_accessible_flashcard_set_ids(user_id):
    """Return IDs of flashcard sets accessible to the current user."""
    return list(FlashcardPermissionService.get_accessible_set_ids(user_id))


def _get_base_items_query(user_id, container_id):
    """Create base query for LearningItem filtered by container."""
    return (FlashcardQueryBuilder(user_id)
            .for_container(container_id)
            .build())


def get_new_only_items(user_id, container_id, session_size):
    """Get new items (not yet learned)."""
    return FlashcardItemService.get_new_items(user_id, container_id, session_size)


def get_due_items(user_id, container_id, session_size):
    """Get items due for review."""
    return FlashcardItemService.get_due_items(user_id, container_id, session_size)


def get_all_review_items(user_id, container_id, session_size):
    """Get all items with learning progress."""
    return FlashcardItemService.get_all_review_items(user_id, container_id, session_size)


def get_hard_items(user_id, container_id, session_size):
    """Get difficult items."""
    return FlashcardItemService.get_hard_items(user_id, container_id, session_size)


def get_mixed_items(user_id, container_id, session_size):
    """Get mixed due + new items."""
    return FlashcardItemService.get_mixed_items(user_id, container_id, session_size)


def get_all_items_for_autoplay(user_id, container_id, session_size):
    """Get all items for autoplay mode."""
    return FlashcardItemService.get_autoplay_items(user_id, container_id, session_size)


def get_sequential_items(user_id, container_id, session_size):
    """Get due or new items in sequential order."""
    return FlashcardItemService.get_sequential_items(user_id, container_id, session_size)


def get_pronunciation_items(user_id, container_id, session_size):
    return FlashcardItemService.get_pronunciation_items(user_id, container_id, session_size)


def get_writing_items(user_id, container_id, session_size):
    return FlashcardItemService.get_writing_items(user_id, container_id, session_size)


def get_quiz_items(user_id, container_id, session_size):
    return FlashcardItemService.get_quiz_items(user_id, container_id, session_size)


def get_essay_items(user_id, container_id, session_size):
    return FlashcardItemService.get_essay_items(user_id, container_id, session_size)


def get_listening_items(user_id, container_id, session_size):
    return FlashcardItemService.get_listening_items(user_id, container_id, session_size)


def get_speaking_items(user_id, container_id, session_size):
    return FlashcardItemService.get_speaking_items(user_id, container_id, session_size)


# =============================================================================
# FUNCTIONS KEPT IN ALGORITHMS.PY (Complex UI Logic)
# =============================================================================

def get_filtered_flashcard_sets(user_id, search_query, search_field, current_filter, page, per_page=FlashcardLearningConfig.DEFAULT_ITEMS_PER_PAGE):
    """
    Get paginated flashcard sets with filtering and user state.
    
    [OPTIMIZED] Uses batch queries instead of N+1 queries.
    """
    current_app.logger.debug(f"get_filtered_flashcard_sets: user={user_id}, filter={current_filter}")
    
    # === PHASE 1: Build base query ===
    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')
    
    user_interacted_ids_subquery = db.session.query(UserContainerState.container_id).filter(
        UserContainerState.user_id == user_id
    ).subquery()

    # Access control based on user role
    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        base_query = base_query.filter(
            or_(
                LearningContainer.creator_user_id == user_id,
                LearningContainer.container_id.in_(user_interacted_ids_subquery),
            )
        )
    else:
        access_conditions = [
            LearningContainer.creator_user_id == user_id,
            LearningContainer.is_public == True,
            LearningContainer.container_id.in_(user_interacted_ids_subquery),
        ]

        contributed_sets_ids = db.session.query(ContainerContributor.container_id).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        ).all()

        if contributed_sets_ids:
            access_conditions.append(LearningContainer.container_id.in_([c.container_id for c in contributed_sets_ids]))

        base_query = base_query.filter(or_(*access_conditions))

    # Apply search filter
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    # === PHASE 2: Apply filter and JOIN UserContainerState ===
    if current_filter == 'archive':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            UserContainerState.is_archived == True
        ).order_by(UserContainerState.last_accessed.desc())
    elif current_filter == 'doing':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            UserContainerState.is_archived == False
        ).order_by(UserContainerState.last_accessed.desc())
    elif current_filter == 'explore':
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        ).add_columns(
            db.literal(False).label('is_archived'),
            db.literal(False).label('is_favorite'),
            db.literal(None).label('last_accessed')
        ).order_by(LearningContainer.created_at.desc())
    else:
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(LearningContainer.created_at.desc())

    # === PHASE 3: Paginate ===
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Extract container IDs and map joined data
    container_ids = []
    user_state_map = {}
    
    for row in pagination.items:
        if isinstance(row, tuple):
            container = row[0]
            user_state_map[container.container_id] = {
                'is_archived': row[1] if row[1] is not None else False,
                'is_favorite': row[2] if row[2] is not None else False,
                'last_accessed': row[3]
            }
        else:
            container = row
            user_state_map[container.container_id] = {'is_archived': False, 'is_favorite': False, 'last_accessed': None}
        container_ids.append(container.container_id)
    
    if not container_ids:
        pagination.items = []
        return pagination
    
    # === PHASE 4: Batch Query for Item Counts ===
    item_counts = db.session.query(
        LearningItem.container_id,
        func.count(LearningItem.item_id).label('total')
    ).filter(
        LearningItem.container_id.in_(container_ids),
        LearningItem.item_type == 'FLASHCARD'
    ).group_by(LearningItem.container_id).all()
    
    item_count_map = {row.container_id: row.total for row in item_counts}
    
    # === PHASE 5: Batch Query for Learned Items ===
    learned_counts = db.session.query(
        LearningItem.container_id,
        func.count(LearningProgress.item_id).label('learned')
    ).join(
        LearningProgress,
        and_(
            LearningProgress.item_id == LearningItem.item_id,
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
    ).filter(
        LearningItem.container_id.in_(container_ids),
        LearningItem.item_type == 'FLASHCARD'
    ).group_by(LearningItem.container_id).all()
    
    learned_count_map = {row.container_id: row.learned for row in learned_counts}
    
    # === PHASE 6: Map batch data to pagination items ===
    processed_items = []
    
    for row in pagination.items:
        if isinstance(row, tuple):
            set_item = row[0]
        else:
            set_item = row
        
        container_id = set_item.container_id
        
        if not hasattr(set_item, 'creator') or set_item.creator is None:
            set_item.creator = type('obj', (object,), {'username': 'Người dùng không xác định'})()
        
        total_items = item_count_map.get(container_id, 0)
        learned_items = learned_count_map.get(container_id, 0)
        
        set_item.item_count_display = f"{learned_items} / {total_items}"
        set_item.total_items = total_items
        set_item.completion_percentage = (learned_items / total_items * 100) if total_items > 0 else 0
        
        state_data = user_state_map.get(container_id, {'is_archived': False, 'is_favorite': False, 'last_accessed': None})
        set_item.user_state = state_data
        set_item.last_accessed = state_data.get('last_accessed')
        
        processed_items.append(set_item)
    
    pagination.items = processed_items
    current_app.logger.debug(f"get_filtered_flashcard_sets: total={pagination.total}")
    return pagination


def get_flashcard_mode_counts(user_id, set_identifier):
    """
    Calculate item counts for each flashcard learning mode.
    """
    current_app.logger.debug(f"get_flashcard_mode_counts: user={user_id}, set={set_identifier}")
    
    try:
        modes_with_counts = []
        mode_function_map = {
            'mixed_srs': get_mixed_items,
            'new_only': get_new_only_items,
            'due_only': get_due_items,
            'all_review': get_all_review_items,
            'hard_only': get_hard_items,
            'sequential': get_sequential_items,
            'pronunciation_practice': get_pronunciation_items,
            'writing_practice': get_writing_items,
            'quiz_practice': get_quiz_items,
            'essay_practice': get_essay_items,
            'listening_practice': get_listening_items,
            'speaking_practice': get_speaking_items,
        }

        for mode_config in FlashcardLearningConfig.FLASHCARD_MODES:
            mode_id = mode_config['id']
            mode_name = mode_config['name']
            algorithm_func = mode_function_map.get(mode_id)
            hide_if_zero = mode_config.get('hide_if_zero', False)

            if algorithm_func:
                if mode_id == 'mixed_srs':
                    due_count = get_due_items(user_id, set_identifier, None).count()
                    new_count = get_new_only_items(user_id, set_identifier, None).count()
                    count = due_count + new_count
                elif mode_id in ('sequential', 'random'):
                    count = get_all_items_for_autoplay(user_id, set_identifier, None).count()
                else:
                    count = algorithm_func(user_id, set_identifier, None).count()

                if hide_if_zero and count == 0:
                    continue

                modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': count})
            else:
                current_app.logger.warning(f"No algorithm function found for mode: {mode_id}")
                modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': 0})

        autoplay_learned_count = get_all_review_items(user_id, set_identifier, None).count()
        autoplay_all_count = get_all_items_for_autoplay(user_id, set_identifier, None).count()
        autoplay_total_count = max(autoplay_learned_count, autoplay_all_count)

        modes_with_counts.append({
            'id': 'autoplay',
            'name': FlashcardLearningConfig.AUTOPLAY_MODE_NAME,
            'count': autoplay_total_count,
            'autoplay_counts': {
                'autoplay_learned': autoplay_learned_count,
                'autoplay_all': autoplay_all_count,
            }
        })

        current_app.logger.debug(f"get_flashcard_mode_counts: modes={modes_with_counts}")
        return modes_with_counts
    except Exception as e:
        current_app.logger.error(f"Error in get_flashcard_mode_counts: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        raise e

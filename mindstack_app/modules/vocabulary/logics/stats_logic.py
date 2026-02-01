# File: vocabulary/logics/stats_logic.py
# Logic for calculating course overview statistics (Vocabulary List)

from datetime import datetime
from sqlalchemy import func, case
from mindstack_app.models import LearningItem, LearningProgress, db
from mindstack_app.utils.content_renderer import render_text_field
from mindstack_app.modules.learning.services.fsrs_service import FsrsService

def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 12) -> dict:
    """
    Get paginated course overview statistics (vocabulary list with progress).
    """
    from flask import current_app
    current_app.logger.debug(f"get_course_overview_stats: user={user_id}, container={container_id}, page={page}")
    # 1. Get all items in the container (FLASHCARD or VOCABULARY type)
    base_query = LearningItem.query.filter(
        LearningItem.container_id == container_id,
        LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
    )
    total_items = base_query.count()
    current_app.logger.debug(f"get_course_overview_stats: total_items={total_items}")
    # 2. Get paginated items (order by position in container, then by ID)
    pagination = base_query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    if not pagination.items:
        current_app.logger.debug("get_course_overview_stats: no items found for this page")
        return {
            'items': [],
            'pagination': {
                'total': total_items,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        }
    item_ids = [item.item_id for item in pagination.items]
    current_app.logger.debug(f"get_course_overview_stats: processing {len(item_ids)} items")
    # 3. Get progress for these items
    progress_records = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
        LearningProgress.item_id.in_(item_ids)
    ).all()
    progress_map = {p.item_id: p for p in progress_records}
    now = datetime.utcnow()
    # 4. Map items to response structure
    result_items = []
    for item in pagination.items:
        try:
            progress = progress_map.get(item.item_id)
            content = item.content or {}
            raw_term = content.get('front', '') or content.get('term', '') or content.get('recto', '') or ''
            raw_definition = content.get('back', '') or content.get('definition', '') or content.get('verso', '') or ''
            term = render_text_field(raw_term)
            definition = render_text_field(raw_definition)
            if progress:
                retrievability = FsrsService.get_retrievability(progress)
                import math
                if math.isnan(retrievability) or math.isinf(retrievability):
                    retrievability = 0.0
                mastery = int(retrievability * 100)  # Proxy for UI
                stability = progress.fsrs_stability or 0.0
                state = progress.fsrs_state
                if state == 0:
                    status = 'new'
                elif state in [1, 3]: # Learning/Relearning
                    status = 'learning'
                elif stability >= 21.0:
                    status = 'mastered'
                else:
                    status = 'reviewing' # Review state (2)
                is_due = progress.fsrs_due and progress.fsrs_due <= now
                memory_level = progress.memory_level if hasattr(progress, 'memory_level') else 0
            else:
                mastery = 0
                retrievability = 0
                status = 'new'
                is_due = False
                memory_level = 0
            result_items.append({
                'item_id': item.item_id,
                'term': term,
                'definition': definition,
                'mastery': mastery,
                'retrievability': retrievability,
                'status': status,
                'is_due': is_due,
                'memory_level': memory_level
            })
        except Exception as e:
            current_app.logger.warning(f"Error processing item {item.item_id}: {e}")
            continue
    current_app.logger.debug(f"get_course_overview_stats: returning {len(result_items)} mapped items")
    return {
        'items': result_items,
        'pagination': {
            'total': total_items,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        },
        'learned_count': db.session.query(func.count(LearningProgress.progress_id))
            .join(LearningItem, LearningProgress.item_id == LearningItem.item_id)
            .filter(
                LearningItem.container_id == container_id,
                LearningProgress.user_id == user_id,
                LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
                LearningProgress.fsrs_state != LearningProgress.STATE_NEW
            ).scalar()
    }

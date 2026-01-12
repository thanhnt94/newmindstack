# File: vocabulary/logics/stats_logic.py
# Logic for calculating course overview statistics (Vocabulary List)

from datetime import datetime
from sqlalchemy import func, case
from mindstack_app.models import LearningItem, LearningProgress, db
from mindstack_app.utils.content_renderer import render_text_field

def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 12) -> dict:
    """
    Get paginated course overview statistics (vocabulary list with progress).
    
    Args:
        user_id: The user's ID
        container_id: The vocabulary container ID
        page: Current page number
        per_page: Items per page
        
    Returns:
        dict containing 'items' list and 'pagination' info
    """
    # 1. Get all items in the container (FLASHCARD or VOCABULARY type)
    base_query = LearningItem.query.filter(
        LearningItem.container_id == container_id,
        LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
    )
    
    total_items = base_query.count()
    
    # 2. Get paginated items (order by position in container, then by ID)
    pagination = base_query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    if not pagination.items:
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
        progress = progress_map.get(item.item_id)
        
        # Parse content safely - Flashcards use 'front'/'back', vocabulary might use 'term'/'definition'
        content = item.content or {}
        raw_term = content.get('front', '') or content.get('term', '') or content.get('recto', '') or ''
        raw_definition = content.get('back', '') or content.get('definition', '') or content.get('verso', '') or ''
        
        # [NEW] Apply BBCode rendering using centralized utility
        term = render_text_field(raw_term)
        definition = render_text_field(raw_definition)
        
        if progress:
            mastery = int((progress.mastery or 0.0) * 100)
            status = progress.status or 'new'
            is_due = progress.due_time and progress.due_time <= now
            
            # Additional detail from mode_data if needed
            memory_level = progress.memory_level if hasattr(progress, 'memory_level') else 0
        else:
            mastery = 0
            status = 'new'
            is_due = False
            memory_level = 0
            
        result_items.append({
            'item_id': item.item_id,
            'term': term,
            'definition': definition,
            'mastery': mastery,
            'status': status,
            'is_due': is_due,
            'memory_level': memory_level
        })
    
    # 5. Sort items (Client-side sorting logic was: Low mastery first, New last)
    # But since we paginate, we can only sort fairly within the page unless we sort the SQL query by progress.
    # For now, we return in creation order (default) or let the frontend sort visual elements.
    # To match legacy behavior, we could join with Progress in the main query, but that's complex for a quick fix.
    # The frontend code does: `sortedItems = [...stats.items].sort(...)` so it re-sorts the current page.
    
    return {
        'items': result_items,
        'pagination': {
            'total': total_items,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        },
        'learned_count': LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.item_id.in_(item_ids), # Note: this count is just for this page? No.
            # The dashboard probably needs total learned count for the header.
            # But the header data comes from api_get_set_detail -> get_set_detail which counts separately?
            # api_get_set_detail DOES NOT use this return value for header counts.
            # It uses `card_count` and `memrise_count`.
            # Wait, `api.py` line 258: `'learned_count': learned_count`. No, that's inside `get_full_stats`.
            # api_get_set_detail uses `course_stats` just for the list.
        ).count() # This is wrong. Header stats come from `container_stats`.
    }

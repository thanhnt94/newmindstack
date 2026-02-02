# File: mindstack_app/modules/vocab_typing/logics/typing_logic.py
from datetime import datetime, timezone
from sqlalchemy import func
from mindstack_app.models import LearningItem, db
from mindstack_app.modules.fsrs.models import ItemMemoryState

def get_typing_items(user_id, mode='new', limit=10):
    """
    Lấy danh sách item cho luyện gõ.
    """
    base_query = LearningItem.query.filter(
        LearningItem.item_type == 'FLASHCARD'
    )
    
    now = datetime.now(timezone.utc)
    
    items = []
    if mode == 'review':
        items = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).order_by(ItemMemoryState.due_date).limit(limit).all()
        
    elif mode == 'mixed':
        items = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).order_by(func.random()).limit(limit).all()
        
    elif mode == 'hard':
        items = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.difficulty >= 7.5
        ).limit(limit).all()
        
    elif mode == 'new':
        items = base_query.outerjoin(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
            (ItemMemoryState.state == None) | (ItemMemoryState.state == 0)
        ).limit(limit).all()
        
    return items
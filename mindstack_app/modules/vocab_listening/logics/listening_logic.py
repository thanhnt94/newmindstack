# File: mindstack_app/modules/vocab_listening/logics/listening_logic.py
from datetime import datetime, timezone
from sqlalchemy import func
from mindstack_app.models import LearningItem
from mindstack_app.modules.fsrs.models import ItemMemoryState

def get_listening_items(user_id, mode='new', limit=10):
    """
    Lấy danh sách item cho luyện nghe.
    mode: 'new', 'review', 'hard', 'mixed'
    """
    base_query = LearningItem.query.filter(
        LearningItem.item_type == 'FLASHCARD',
        # Chỉ lấy item có audio
        # LearningItem.content['audio'].astext != None # Postgres specific
        # SQLite doesn't support easy JSON filtering, rely on app logic or filter later
    )
    
    # Filter items that actually have content to listen to (basic check)
    # Since we can't easily filter JSON in SQLite efficiently without extension, 
    # we might filter in Python or assume Flashcards generally have audio if generated.
    
    now = datetime.now(timezone.utc)
    
    if mode == 'review':
        # Due items
        base_query = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).order_by(ItemMemoryState.due_date)
    elif mode == 'hard':
        # Difficulty high
        base_query = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.difficulty >= 7.5
        )
    elif mode == 'new':
        # Not in ItemMemoryState OR state=NEW
        # Outer join
        base_query = base_query.outerjoin(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
            (ItemMemoryState.state == None) | (ItemMemoryState.state == 0)
        )
    elif mode == 'mixed':
        # Random mix of learned items
        base_query = base_query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).order_by(func.random())
        
    items = base_query.limit(limit * 2).all() # Fetch more to filter by audio existence
    
    valid_items = []
    for item in items:
        content = item.content or {}
        # Check if has audio (front or back)
        if content.get('audio') or content.get('front_audio_url') or content.get('back_audio_url'):
            valid_items.append(item)
            if len(valid_items) >= limit:
                break
                
    return valid_items
# File: mindstack_app/modules/vocab_listening/logics/listening_logic.py
from datetime import datetime, timezone
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface

def get_listening_items(user_id, container_id=None, mode='new', limit=10):
    """
    Lấy danh sách item cho luyện nghe.
    mode: 'new', 'review', 'hard', 'mixed'
    """
    # Fetch candidate items using FSRS Interface
    # Limit bumped to 2x to account for audio filtering
    candidate_items = FsrsInterface.get_items_for_practice(
        user_id=user_id,
        container_id=container_id,
        mode=mode, 
        limit=limit * 2, 
        item_type='FLASHCARD'
    )
    
    valid_items = []
    for item in candidate_items:
        content = item.content or {}
        # Check if has audio (front or back)
        if content.get('audio') or content.get('front_audio_url') or content.get('back_audio_url'):
            valid_items.append(item)
            if len(valid_items) >= limit:
                break
                
    return valid_items
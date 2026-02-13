# File: mindstack_app/modules/vocab_typing/logics/typing_logic.py
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface

def get_typing_items(user_id, container_id=None, mode='all', limit=10):
    """
    Lấy danh sách item cho luyện gõ.
    Delegates to FsrsInterface.
    """
    return FsrsInterface.get_items_for_practice(
        user_id=user_id,
        container_id=container_id,
        mode=mode,
        limit=limit,
        item_type='FLASHCARD'
    )
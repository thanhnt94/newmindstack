# File: mindstack_app/modules/learning/flashcard_learning/config.py
# Phiên bản: 1.0
# Mục đích: Chứa các cấu hình riêng cho module học Flashcard.

class FlashcardLearningConfig:
    """
    Cấu hình cho module học Flashcard.
    """
    DEFAULT_ITEMS_PER_PAGE = 3 # Số mục mặc định trên mỗi trang cho Flashcard

    # Số thẻ mặc định trong một nhóm (batch) cho phiên học Flashcard
    FLASHCARD_DEFAULT_BATCH_SIZE = 10 

    # Định nghĩa các chế độ học Flashcard
    FLASHCARD_MODES = [
        {'id': 'new_only', 'name': 'Chỉ học thẻ mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'due_only', 'name': 'Ôn tập thẻ đến hạn', 'algorithm_func_name': 'get_due_items'},
        {'id': 'hard_only', 'name': 'Ôn tập thẻ khó', 'algorithm_func_name': 'get_hard_items'},
    ]
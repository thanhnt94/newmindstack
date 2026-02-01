# File: mindstack_app/modules/learning/flashcard_learning/config.py
# Phiên bản: 1.2
# Mục đích: Chứa các cấu hình riêng cho module học Flashcard.
# ĐÃ THÊM: Chế độ học "Học và ôn tập (đan xen)" mới.

class FlashcardLearningConfig:
    """
    Cấu hình cho module học Flashcard.
    """
    DEFAULT_ITEMS_PER_PAGE = 12 # Số mục mặc định trên mỗi trang cho Flashcard
    AUTOPLAY_MODE_NAME = 'Chế độ AutoPlay'

    # Định nghĩa các chế độ học Flashcard
    # THAY ĐỔI: Thêm chế độ học "Học và ôn tập" lên đầu danh sách
    
    FLASHCARD_MODES = [
        {'id': 'sequential', 'name': 'Học tập tuần tự', 'algorithm_func_name': 'get_sequential_items'},
        {'id': 'all_review', 'name': 'Ôn tập thẻ đã học', 'algorithm_func_name': 'get_all_review_items'},
        {'id': 'new_only', 'name': 'Chỉ học thẻ mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'hard_only', 'name': 'Ôn tập thẻ khó', 'algorithm_func_name': 'get_hard_items'},
    ]

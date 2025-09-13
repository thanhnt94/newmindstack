# File: mindstack_app/modules/learning/flashcard_learning/config.py
# Phiên bản: 1.2
# Mục đích: Chứa các cấu hình riêng cho module học Flashcard.
# ĐÃ THÊM: Chế độ học "Học và ôn tập (đan xen)" mới.

class FlashcardLearningConfig:
    """
    Cấu hình cho module học Flashcard.
    """
    DEFAULT_ITEMS_PER_PAGE = 12 # Số mục mặc định trên mỗi trang cho Flashcard

    # Định nghĩa các chế độ học Flashcard
    # THAY ĐỔI: Thêm chế độ học "Học và ôn tập" lên đầu danh sách
    FLASHCARD_MODES = [
        {'id': 'mixed_srs', 'name': 'Học tập tuần tự', 'algorithm_func_name': 'get_mixed_items'},
        {'id': 'new_only', 'name': 'Chỉ học thẻ mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'due_only', 'name': 'Ôn tập thẻ đến hạn', 'algorithm_func_name': 'get_due_items'},
        {'id': 'hard_only', 'name': 'Ôn tập thẻ khó', 'algorithm_func_name': 'get_hard_items'},
    ]
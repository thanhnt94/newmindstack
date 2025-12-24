# Quiz Engine Configuration
# Contains settings and mode definitions for quiz learning.

class QuizConfig:
    """Configuration for Quiz learning module."""
    
    # Default items per page
    DEFAULT_ITEMS_PER_PAGE = 3
    
    # Default batch size for quiz sessions
    DEFAULT_BATCH_SIZE = 1
    
    # Quiz display modes
    DISPLAY_MODES = {
        'single': 'Từng câu một',
        'batch': 'Nhiều câu một lúc',
    }
    
    # Quiz question modes
    QUESTION_MODES = [
        {'id': 'front_back', 'name': 'Mặt trước → Mặt sau'},
        {'id': 'back_front', 'name': 'Mặt sau → Mặt trước'},
        {'id': 'mixed', 'name': 'Ngẫu nhiên hai chiều'},
        {'id': 'custom', 'name': 'Tùy chỉnh cặp hỏi-đáp'},
    ]
    
    # SRS-based learning modes
    QUIZ_MODES = [
        {'id': 'new_only', 'name': 'Chỉ làm mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'due_only', 'name': 'Ôn tập câu đã làm', 'algorithm_func_name': 'get_reviewed_items'},
        {'id': 'hard_only', 'name': 'Ôn tập câu khó', 'algorithm_func_name': 'get_hard_items'},
        {'id': 'mixed_srs', 'name': 'Học và ôn tập', 'algorithm_func_name': 'get_mixed_items'},
    ]

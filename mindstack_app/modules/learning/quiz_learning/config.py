# File: mindstack_app/modules/learning/quiz_learning/config.py
# Phiên bản: 1.2
# Mục đích: Chứa các cấu hình riêng cho module học Quiz.
# ĐÃ THÊM: Định nghĩa tập trung các chế độ học Quiz (QUIZ_MODES).
# ĐÃ THÊM: QUIZ_DEFAULT_BATCH_SIZE để lưu cài đặt mặc định số câu hỏi.

class QuizLearningConfig:
    """
    Cấu hình cho module học Quiz.
    """
    DEFAULT_ITEMS_PER_PAGE = 12 # Số mục mặc định trên mỗi trang cho Quiz

    # THÊM MỚI: Số câu hỏi mặc định trong một nhóm (batch) cho phiên học Quiz
    QUIZ_DEFAULT_BATCH_SIZE = 10 

    # Định nghĩa các chế độ học Quiz
    QUIZ_MODES = [
        {'id': 'new_only', 'name': 'Chỉ làm mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'due_only', 'name': 'Ôn tập câu đã làm', 'algorithm_func_name': 'get_reviewed_items'},
        {'id': 'hard_only', 'name': 'Ôn tập câu khó', 'algorithm_func_name': 'get_hard_items'},
        # Thêm các chế độ học khác tại đây nếu cần
        # Ví dụ: {'id': 'random_all', 'name': 'Ngẫu nhiên tất cả', 'algorithm_func_name': 'get_all_items_randomly'},
    ]

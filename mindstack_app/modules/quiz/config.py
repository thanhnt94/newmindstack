# File: mindstack_app/modules/quiz/config.py

class QuizLearningConfig:
    """
    Cấu hình mặc định cho module Quiz.
    """
    DEFAULT_ITEMS_PER_PAGE = 3
    QUIZ_DEFAULT_BATCH_SIZE = 1 

    QUIZ_MODES = [
        {'id': 'new_only', 'name': 'Chỉ làm mới', 'algorithm_func_name': 'get_new_only_items'},
        {'id': 'due_only', 'name': 'Ôn tập câu đã làm', 'algorithm_func_name': 'get_reviewed_items'},
        {'id': 'hard_only', 'name': 'Ôn tập câu khó', 'algorithm_func_name': 'get_hard_items'},
    ]

# Alias for backward compatibility or different naming conventions used in refactor
QuizModuleDefaultConfig = QuizLearningConfig

# File: mindstack_app/modules/learning/flashcard_learning/config.py
# Phiên bản: 1.2
# Mục đích: Chứa các cấu hình riêng cho module học Flashcard.
# ĐÃ THÊM: Chế độ học "Học và ôn tập (đan xen)" mới.

class FlashcardLearningConfig:
    """
    Cấu hình cho module học Flashcard.
    """

    DEFAULT_ITEMS_PER_PAGE = 12  # Số mục mặc định trên mỗi trang cho Flashcard
    AUTOPLAY_MODE_NAME = 'Chế độ AutoPlay'

    # Định nghĩa các nhóm chế độ học Flashcard để giao diện có thể hiển thị theo cụm.
    # Mỗi nhóm bao gồm metadata hiển thị (icon, mô tả) và danh sách chế độ con.
    FLASHCARD_MODE_GROUPS = [
        {
            'id': 'flashcard',
            'title': 'Ôn tập thẻ',
            'description': 'Các chế độ học truyền thống và AutoPlay giúp bạn xoay vòng thẻ linh hoạt.',
            'icon': 'fas fa-layer-group',
            'modes': [
                {
                    'id': 'mixed_srs',
                    'name': 'Học tập tuần tự',
                    'description': 'Kết hợp thẻ mới và thẻ đến hạn theo thuật toán SRS.',
                    'algorithm_func_name': 'get_mixed_items',
                },
                {
                    'id': 'new_only',
                    'name': 'Chỉ học thẻ mới',
                    'description': 'Tập trung vào những thẻ bạn chưa từng xem.',
                    'algorithm_func_name': 'get_new_only_items',
                },
                {
                    'id': 'due_only',
                    'name': 'Ôn tập thẻ đến hạn',
                    'description': 'Ôn những thẻ đến hạn theo lịch SRS.',
                    'algorithm_func_name': 'get_due_items',
                },
                {
                    'id': 'all_review',
                    'name': 'Ôn tập toàn bộ thẻ đã học',
                    'description': 'Làm mới toàn bộ kiến thức với những thẻ đã có tiến độ.',
                    'algorithm_func_name': 'get_all_review_items',
                },
                {
                    'id': 'hard_only',
                    'name': 'Ôn tập thẻ khó',
                    'description': 'Rèn luyện chuyên sâu với các thẻ bạn thường đánh giá là khó.',
                    'algorithm_func_name': 'get_hard_items',
                },
                {
                    'id': 'autoplay',
                    'name': AUTOPLAY_MODE_NAME,
                    'description': 'Nghe phát lại mặt trước và sau của thẻ hoàn toàn tự động.',
                    'is_autoplay': True,
                },
            ],
        },
        {
            'id': 'listening',
            'title': 'Luyện nghe',
            'description': 'Các hoạt động luyện nghe chuyên sâu sẽ được ra mắt sớm.',
            'icon': 'fas fa-headphones',
            'modes': [],
            'is_placeholder': True,
            'placeholder_copy': 'Chúng tôi đang xây dựng các chế độ luyện nghe mới. Hãy quay lại sau!',
        },
        {
            'id': 'speaking',
            'title': 'Luyện nói',
            'description': 'Ghi âm và so sánh phát âm để cải thiện khả năng nói.',
            'icon': 'fas fa-microphone-alt',
            'modes': [
                {
                    'id': 'pronunciation_practice',
                    'name': 'Luyện phát âm',
                    'description': 'Nghe mẫu và luyện nói theo từng thẻ.',
                    'algorithm_func_name': 'get_pronunciation_items',
                    'capability_flag': 'supports_pronunciation',
                    'hide_if_zero': True,
                },
            ],
        },
        {
            'id': 'quiz',
            'title': 'Trắc nghiệm',
            'description': 'Kiểm tra nhanh với các câu hỏi trắc nghiệm.',
            'icon': 'fas fa-question-circle',
            'modes': [
                {
                    'id': 'quiz_practice',
                    'name': 'Luyện trắc nghiệm',
                    'description': 'Chọn đáp án đúng để kiểm tra khả năng ghi nhớ.',
                    'algorithm_func_name': 'get_quiz_items',
                    'capability_flag': 'supports_quiz',
                    'hide_if_zero': True,
                },
            ],
        },
        {
            'id': 'writing',
            'title': 'Luyện viết',
            'description': 'Ghi nhớ bằng cách viết lại đáp án hoặc chữ cái.',
            'icon': 'fas fa-pen-fancy',
            'modes': [
                {
                    'id': 'writing_practice',
                    'name': 'Luyện viết',
                    'description': 'Luyện viết lại đáp án của thẻ.',
                    'algorithm_func_name': 'get_writing_items',
                    'capability_flag': 'supports_writing',
                    'hide_if_zero': True,
                },
            ],
        },
    ]

    # Tra cứu nhanh metadata của từng chế độ theo ID và danh sách phẳng phục vụ các logic cũ.
    _mode_map = {}
    _flat_modes = []
    for _group in FLASHCARD_MODE_GROUPS:
        for _mode in _group.get('modes', []):
            mode_id = _mode['id']
            mode_metadata = {
                **_mode,
                'group_id': _group['id'],
                'group_title': _group.get('title'),
                'group_icon': _group.get('icon'),
                'group_description': _group.get('description'),
                'group_placeholder_copy': _group.get('placeholder_copy'),
                'group_is_placeholder': _group.get('is_placeholder', False),
            }
            _mode_map[mode_id] = mode_metadata
            if not mode_metadata.get('is_autoplay'):
                _flat_modes.append(mode_metadata)

    FLASHCARD_MODE_MAP = _mode_map
    FLASHCARD_MODES = _flat_modes

    del _mode_map
    del _flat_modes

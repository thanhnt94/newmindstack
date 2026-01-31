"""Shared configuration for learning goals."""

from __future__ import annotations

# Legacy config - keeping for backward compatibility if needed, though we will likely migrate logic
GOAL_TYPE_CONFIG: dict[str, dict[str, str]] = {
    'flashcards_reviewed': {
        'label': 'Flashcard',
        'description': 'Ôn luyện flashcard và giữ chuỗi học.',
        'unit': 'thẻ',
        'icon': 'clone',
        'endpoint': 'flashcard.flashcard_dashboard_internal.dashboard',
    },
    'quizzes_practiced': {
        'label': 'Quiz',
        'description': 'Luyện quiz để củng cố kiến thức.',
        'unit': 'câu',
        'icon': 'circle-question',
        'endpoint': 'quiz.dashboard',
        'color': 'indigo',
    },
    'lessons_completed': {
        'label': 'Bài học',
        'description': 'Hoàn thành các bài học trong khóa.',
        'unit': 'bài',
        'icon': 'graduation-cap',
        'endpoint': 'course.course_learning_dashboard',
    },
}

PERIOD_LABELS: dict[str, str] = {
    'daily': 'Hôm nay',
    'weekly': '7 ngày qua',
    'total': 'Tổng cộng',
}

PERIOD_CHOICES: list[tuple[str, str]] = [
    ('daily', 'Hàng ngày'),
    ('weekly', 'Hàng tuần'),
    ('monthly', 'Hàng tháng'),
    ('total', 'Tổng cộng (Dài hạn)'),
]

DOMAIN_CHOICES = [
    ('general', 'Tổng hợp (Điểm số)'),
    ('flashcard', 'Flashcards'),
    ('quiz', 'Quiz (Trắc nghiệm)'),
    # ('course', 'Khóa học'), # Future
]

SCOPE_CHOICES = [
    ('global', 'Toàn bộ hệ thống'),
    ('container', 'Bộ học liệu cụ thể'),
]

METRIC_CHOICES = {
    'general': [
        ('points', 'Điểm tổng (XP)'),
    ],
    'flashcard': [
        ('items_reviewed', 'Số thẻ đã ôn tập'),
        ('new_items', 'Số thẻ mới đã học'),
        ('time_spent', 'Thời gian học (phút)'),
    ],
    'quiz': [
        ('items_answered', 'Số câu đã trả lời'),
        ('items_correct', 'Số câu trả lời đúng'),
        ('accuracy', 'Độ chính xác trung bình (%)'), # Maybe tricky to aggregate
        ('points', 'Điểm Quiz kiếm được'),
    ]
}

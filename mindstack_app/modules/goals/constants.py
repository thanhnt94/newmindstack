"""Shared configuration for learning goals."""

from __future__ import annotations

GOAL_TYPE_CONFIG: dict[str, dict[str, str]] = {
    'flashcards_reviewed': {
        'label': 'Flashcard',
        'description': 'Ôn luyện flashcard và giữ chuỗi học.',
        'unit': 'thẻ',
        'icon': 'clone',
        'endpoint': 'learning.flashcard.dashboard',
    },
    'quizzes_practiced': {
        'label': 'Quiz',
        'description': 'Luyện quiz để củng cố kiến thức.',
        'unit': 'câu',
        'icon': 'circle-question',
        'endpoint': 'learning.quiz_learning.quiz_learning_dashboard',
    },
    'lessons_completed': {
        'label': 'Bài học',
        'description': 'Hoàn thành các bài học trong khóa.',
        'unit': 'bài',
        'icon': 'graduation-cap',
        'endpoint': 'learning.course_learning.course_learning_dashboard',
    },
}

PERIOD_LABELS: dict[str, str] = {
    'daily': 'Hôm nay',
    'weekly': '7 ngày qua',
    'total': 'Tổng cộng',
}

PERIOD_CHOICES: list[tuple[str, str]] = [
    ('daily', PERIOD_LABELS['daily']),
    ('weekly', PERIOD_LABELS['weekly']),
    ('total', PERIOD_LABELS['total']),
]

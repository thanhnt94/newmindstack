"""Database models package for Mindstack."""

from mindstack_app.core.extensions import db

# Modules-based models
from mindstack_app.modules.auth.models import User, UserSession
from mindstack_app.modules.learning.models import (
    LearningContainer, 
    LearningGroup, 
    LearningItem, 
    LearningProgress, 
    LearningSession,
    UserContainerState,
    ContainerContributor,
    ReviewLog,
    UserItemMarker
)
from mindstack_app.modules.vocab_flashcard.models import (
    FlashcardSet,
    Flashcard,
    FlashcardCollabAnswer,
    FlashcardCollabMessage,
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    FlashcardCollabRound,
    FlashcardRoomProgress,
)
from mindstack_app.modules.quiz.models import (
    QuizSet, 
    QuizMCQ,
    QuizBattleAnswer,
    QuizBattleMessage,
    QuizBattleParticipant,
    QuizBattleRoom,
    QuizBattleRound,
)
from mindstack_app.modules.AI.models import ApiKey, AiTokenLog, AiCache
from mindstack_app.modules.goals.models import Goal, UserGoal, GoalProgress
from mindstack_app.modules.gamification.models import Badge, UserBadge, ScoreLog, Streak
from mindstack_app.modules.translator.models import TranslationHistory
from mindstack_app.modules.stats.models import UserMetric, DailyStat, Achievement
from mindstack_app.modules.notification.models import Notification, PushSubscription, NotificationPreference
from mindstack_app.modules.feedback.models import Feedback, FeedbackAttachment
from mindstack_app.modules.notes.models import Note

# Core models (Legacy or shared)
from .course import Course, Lesson
from .system import BackgroundTask, BackgroundTaskLog
from .app_settings import AppSettings

__all__ = [
    'db',
    'User',
    'UserSession',
    'LearningContainer',
    'LearningGroup',
    'LearningItem',
    'LearningProgress',
    'LearningSession',
    'UserContainerState',
    'ContainerContributor',
    'ReviewLog',
    'UserItemMarker',
    'FlashcardSet',
    'Flashcard',
    'FlashcardCollabAnswer',
    'FlashcardCollabMessage',
    'FlashcardCollabParticipant',
    'FlashcardCollabRoom',
    'FlashcardCollabRound',
    'FlashcardRoomProgress',
    'QuizSet',
    'QuizMCQ',
    'QuizBattleAnswer',
    'QuizBattleMessage',
    'QuizBattleParticipant',
    'QuizBattleRoom',
    'QuizBattleRound',
    'ApiKey',
    'AiTokenLog',
    'AiCache',
    'Goal',
    'UserGoal',
    'GoalProgress',
    'Badge',
    'UserBadge',
    'ScoreLog',
    'Streak',
    'TranslationHistory',
    'UserMetric',
    'DailyStat',
    'Achievement',
    'Notification',
    'PushSubscription',
    'NotificationPreference',
    'Feedback',
    'FeedbackAttachment',
    'Note',
    'Course',
    'Lesson',
    'BackgroundTask',
    'BackgroundTaskLog',
    'AppSettings',
]

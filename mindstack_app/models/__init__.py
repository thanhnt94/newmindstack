"""Database models package for Mindstack."""

from mindstack_app.core.extensions import db

# Modules-based models
from mindstack_app.modules.auth.models import User, UserSession
from mindstack_app.modules.learning.models import (
    LearningContainer, 
    LearningGroup, 
    LearningItem, 
    LearningSession,
    UserContainerState,
    ContainerContributor,
    UserItemMarker
)
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.learning_history.models import StudyLog

# Core learning models (without collab)
from mindstack_app.modules.vocab_flashcard.models import (
    FlashcardSet,
    Flashcard,
)
from mindstack_app.modules.quiz.models import (
    QuizSet, 
    QuizMCQ,
)

# Collab models (centralized in collab module)
from mindstack_app.modules.collab.models import (
    FlashcardCollabRoom,
    FlashcardCollabParticipant,
    FlashcardCollabMessage,
    FlashcardCollabRound,
    FlashcardCollabAnswer,
    FlashcardRoomProgress,
    QuizBattleRoom,
    QuizBattleParticipant,
    QuizBattleRound,
    QuizBattleAnswer,
    QuizBattleMessage,
)

from mindstack_app.modules.AI.models import ApiKey, AiTokenLog, AiCache, AiContent
from mindstack_app.modules.goals.models import Goal, UserGoal, GoalProgress
from mindstack_app.modules.gamification.models import Badge, UserBadge, ScoreLog, Streak
from mindstack_app.modules.translator.models import TranslationHistory
from mindstack_app.modules.stats.models import UserMetric, DailyStat, Achievement
from mindstack_app.modules.notification.models import Notification, PushSubscription, NotificationPreference
from mindstack_app.modules.feedback.models import Feedback, FeedbackAttachment
from mindstack_app.modules.notes.models import Note
from mindstack_app.modules.content_generator.models import GenerationLog

# Module-based models (formerly in models/)
from mindstack_app.modules.course.models import Course, Lesson
from mindstack_app.modules.ops.models import BackgroundTask, BackgroundTaskLog
from .app_settings import AppSettings

__all__ = [
    'db',
    'User',
    'UserSession',
    'LearningContainer',
    'LearningGroup',
    'LearningItem',
    'ItemMemoryState',
    'LearningSession',
    'UserContainerState',
    'ContainerContributor',
    'StudyLog',
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
    'AiContent',
    'GenerationLog',
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
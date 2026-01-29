"""Database models package for Mindstack."""

from ..db_instance import db

from .learning import LearningContainer, LearningGroup, LearningItem
from .flashcard_collab import (
    FlashcardCollabAnswer,
    FlashcardCollabMessage,
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    FlashcardCollabRound,
    FlashcardRoomProgress,
)
from .quiz_battle import (
    QuizBattleAnswer,
    QuizBattleMessage,
    QuizBattleParticipant,
    QuizBattleRoom,
    QuizBattleRound,
)
from .user import (
    User,
    UserContainerState,
    UserSession,


    UserNote,
    ContainerContributor,
    ReviewLog,
    UserItemMarker,
)
from .system import BackgroundTask, BackgroundTaskLog
from .ai import ApiKey, AiTokenLog, AiCache
from .app_settings import AppSettings  # unified settings (replaces SiteSettings + SystemSetting)
from .learning_progress import LearningProgress  # NEW: Unified progress model
from .learning_session import LearningSession  # NEW: Database-backed sessions
from .goals import Goal, UserGoal, GoalProgress  # NEW: Centralized Goal System
from .gamification import Badge, UserBadge, ScoreLog, Streak
from .translator import TranslationHistory
from .stats import UserMetric, DailyStat, Achievement  # NEW: Stats Module Models
from .notification import Notification, PushSubscription, NotificationPreference # NEW: Notification Models
from .feedback import Feedback, FeedbackAttachment # NEW: Feedback Models

__all__ = [
    'db',
    'LearningContainer',
    'LearningGroup',
    'LearningItem',
    'LearningProgress',  # NEW
    'LearningSession',  # NEW
    'FlashcardCollabAnswer',
    'FlashcardCollabMessage',
    'FlashcardCollabParticipant',
    'FlashcardCollabRoom',
    'FlashcardCollabRound',
    'FlashcardRoomProgress',
    'QuizBattleAnswer',
    'QuizBattleMessage',
    'QuizBattleParticipant',
    'QuizBattleRoom',
    'QuizBattleRound',
    'User',
    'UserContainerState',
    'UserSession',
    'ScoreLog',
    'Goal',            # NEW
    'UserGoal',        # NEW
    'GoalProgress',    # NEW
    'UserNote',
    'ContainerContributor',
    'ContainerContributor',
    'ReviewLog',
    'UserItemMarker',
    'BackgroundTask',
    'BackgroundTaskLog',
    'ApiKey',
    'AiTokenLog',
    'AiCache',
    'Badge',
    'UserBadge',
    'ScoreLog',
    'Streak',
    'AppSettings',
    'TranslationHistory',
    'UserMetric',
    'DailyStat',
    'Achievement',
    'Notification',
    'PushSubscription',
    'NotificationPreference',
    'Feedback',
    'FeedbackAttachment',
]

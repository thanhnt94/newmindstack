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
    ScoreLog,

    UserNote,
    UserFeedback,
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
from .gamification import Badge, UserBadge
from .translator import TranslationHistory
from .stats import UserMetric, DailyStat, Achievement  # NEW: Stats Module Models

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
    'UserFeedback',
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
    'AppSettings',
    'TranslationHistory',
    'UserMetric',
    'DailyStat',
    'Achievement',
]

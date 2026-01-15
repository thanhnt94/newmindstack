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
    LearningGoal,
    GoalDailyHistory,
    UserNote,
    UserFeedback,
    ContainerContributor,
    ReviewLog,
    UserItemMarker,
)
from .system import ApiKey, BackgroundTask, BackgroundTaskLog
from .app_settings import AppSettings  # unified settings (replaces SiteSettings + SystemSetting)
from .learning_progress import LearningProgress  # NEW: Unified progress model
from .learning_session import LearningSession  # NEW: Database-backed sessions
from .gamification import Badge, UserBadge
from .translator import TranslationHistory

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
    'LearningGoal',
    'GoalDailyHistory',
    'UserNote',
    'UserFeedback',
    'ContainerContributor',
    'ContainerContributor',
    'ReviewLog',
    'UserItemMarker',
    'BackgroundTask',
    'BackgroundTaskLog',
    'ApiKey',
    'Badge',
    'UserBadge',
    'AppSettings',
    'TranslationHistory',
]

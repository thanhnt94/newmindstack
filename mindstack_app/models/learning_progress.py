"""Unified Learning Progress model.

This module provides a single unified model to track learning progress
across all learning modes (flashcard, quiz, memrise, etc.), replacing
the separate FlashcardProgress, QuizProgress, and MemriseProgress tables.
"""

from __future__ import annotations

from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db


class LearningProgress(db.Model):
    """Unified progress tracking for all learning modes.
    
    This model consolidates what was previously stored in:
    - FlashcardProgress
    - QuizProgress  
    - MemriseProgress
    - CourseProgress
    
    The `learning_mode` field acts as a discriminator to identify the
    type of learning activity this progress record belongs to.
    """
    
    __tablename__ = 'learning_progress'
    
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    # Learning Mode Discriminator
    # Values: 'flashcard', 'quiz', 'memrise', 'typing', 'listening', 'course'
    learning_mode = db.Column(db.String(20), nullable=False, index=True)
    
    # === SRS Core Fields (SM-2 Algorithm) ===
    status = db.Column(db.String(50), default='new')  # new, learning, reviewing, mastered, hard
    due_time = db.Column(db.DateTime(timezone=True))
    easiness_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)  # minutes
    repetitions = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime(timezone=True))
    first_seen = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # === Memory Power System ===
    mastery = db.Column(db.Float, default=0.0)  # 0.0 - 1.0
    
    # === Statistics ===
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    times_vague = db.Column(db.Integer, default=0)  # Flashcard-specific, NULL for others
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    vague_streak = db.Column(db.Integer, default=0)  # Flashcard-specific
    
    # === Mode-Specific Extended Data ===
    # Memrise: {"memory_level": 5, "session_reps": 3, "current_streak": 2}
    # Course: {"completion_percentage": 75}
    # Quiz/Flashcard: typically empty or {"last_answer": "A"}
    mode_data = db.Column(JSON, nullable=True)
    
    # === Native FSRS-5 Columns ===
    # These are the proper FSRS state variables, replacing legacy EF/interval hybrid
    fsrs_stability = db.Column(db.Float, default=0.0, nullable=True)  # S - memory stability in days
    fsrs_difficulty = db.Column(db.Float, default=5.0, nullable=True)  # D - item difficulty (1-10)
    fsrs_state = db.Column(db.Integer, default=0, nullable=True)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    fsrs_last_review = db.Column(db.DateTime(timezone=True), nullable=True)  # Last FSRS review timestamp (UTC)
    
    # FSRS State Constants
    FSRS_STATE_NEW = 0
    FSRS_STATE_LEARNING = 1
    FSRS_STATE_REVIEW = 2
    FSRS_STATE_RELEARNING = 3
    
    # Relationships
    user = db.relationship(
        'User',
        backref=db.backref('learning_progress', lazy='dynamic', cascade='all, delete-orphan'),
        lazy=True,
    )
    item = db.relationship(
        'LearningItem',
        backref=db.backref('progress_records', lazy='dynamic', cascade='all, delete-orphan'),
        lazy=True,
    )
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', 'learning_mode', name='uq_user_item_mode'),
        db.Index('ix_learning_progress_due', 'user_id', 'learning_mode', 'due_time'),
        db.Index('ix_learning_progress_status', 'user_id', 'learning_mode', 'status'),
        db.Index('ix_learning_progress_user_mode', 'user_id', 'learning_mode'),
    )
    
    # === Mode Constants ===
    MODE_FLASHCARD = 'flashcard'
    MODE_QUIZ = 'quiz'
    MODE_MEMRISE = 'memrise'
    MODE_TYPING = 'typing'
    MODE_LISTENING = 'listening'
    MODE_COURSE = 'course'
    
    def to_dict(self) -> dict:
        """Serialize progress to dictionary."""
        return {
            'progress_id': self.progress_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'learning_mode': self.learning_mode,
            'status': self.status,
            'due_time': self.due_time.isoformat() if self.due_time else None,
            'mastery': self.mastery,
            'times_correct': self.times_correct,
            'times_incorrect': self.times_incorrect,
            'correct_streak': self.correct_streak,
            'mode_data': self.mode_data,
        }
    
    # === Memrise Compatibility Properties ===
    @property
    def memory_level(self) -> int:
        """Get Memrise memory level from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('memory_level', 0)
        return 0
    
    @memory_level.setter
    def memory_level(self, value: int) -> None:
        """Set Memrise memory level in mode_data."""
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['memory_level'] = value
    
    @property
    def session_reps(self) -> int:
        """Get Memrise session reps from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('session_reps', 0)
        return 0
    
    @session_reps.setter
    def session_reps(self, value: int) -> None:
        """Set Memrise session reps in mode_data."""
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['session_reps'] = value
    
    @property
    def current_streak(self) -> int:
        """Get Memrise current streak from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('current_streak', 0)
        return self.correct_streak  # Fallback to correct_streak
    
    @current_streak.setter 
    def current_streak(self, value: int) -> None:
        """Set Memrise current streak in mode_data."""
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['current_streak'] = value
    
    @property
    def level_name(self) -> str:
        """Human-readable name for Memrise memory level."""
        if self.learning_mode != self.MODE_MEMRISE:
            return self.status or 'Unknown'
        
        names = {
            0: 'Chưa học',
            1: 'Mới xem',
            2: 'Đang nhớ',
            3: 'Tạm nhớ',
            4: 'Nhớ khá',
            5: 'Nhớ tốt',
            6: 'Gần thuộc',
            7: 'Đã thuộc',
        }
        return names.get(self.memory_level, 'Unknown')
    
    @property
    def level_percentage(self) -> int:
        """Memrise progress percentage (0-100)."""
        if self.learning_mode != self.MODE_MEMRISE:
            return int(self.mastery * 100)
        return min(100, int((self.memory_level / 7) * 100))
    
    # === Course Compatibility Properties ===
    @property
    def completion_percentage(self) -> int:
        """Get course completion percentage from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('completion_percentage', 0)
        return 0
    
    @completion_percentage.setter
    def completion_percentage(self, value: int) -> None:
        """Set course completion percentage in mode_data."""
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['completion_percentage'] = value

# === Backward Compatibility Aliases ===
# These allow existing code to work during transition period
# TODO: Remove after full migration

    # Alias for FlashcardProgress.first_seen_timestamp
    @property
    def first_seen_timestamp(self):
        """Backward compatible alias for first_seen."""
        return self.first_seen
    
    @first_seen_timestamp.setter
    def first_seen_timestamp(self, value):
        """Backward compatible alias for first_seen."""
        self.first_seen = value
    
    # Legacy review_history column (now stored in ReviewLog table)
    @property
    def review_history(self):
        """Legacy review_history - always returns empty list.
        
        Review history is now stored in the ReviewLog table.
        Use ReviewLog.query.filter_by(user_id=..., item_id=...) instead.
        """
        return []


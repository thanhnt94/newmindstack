"""Unified Learning Progress model (FSRS v5 Native).

This module provides a single unified model to track learning progress
across all learning modes (flashcard, quiz, memrise, etc.) using
the native FSRS-5 algorithm.
"""

from __future__ import annotations

from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db


class LearningProgress(db.Model):
    """Unified FSRS-5 progress tracking for all learning modes.
    
    This model uses native FSRS-5 state variables:
    - stability: Memory stability in days (S)
    - difficulty: Item difficulty 1-10 (D)
    - state: Card state (New/Learning/Review/Relearning)
    """
    
    __tablename__ = 'learning_progress'
    
    # === Primary Keys ===
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    # === Learning Mode Discriminator ===
    learning_mode = db.Column(db.String(20), nullable=False, index=True)
    
    # === FSRS-5 Core State ===
    fsrs_stability = db.Column(db.Float, default=0.0)  # S - memory stability in days
    fsrs_difficulty = db.Column(db.Float, default=5.0)  # D - item difficulty (1-10)
    fsrs_state = db.Column(db.Integer, default=0)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    
    # === Scheduling ===
    fsrs_due = db.Column(db.DateTime(timezone=True), index=True)  # Next review due time (UTC)
    fsrs_last_review = db.Column(db.DateTime(timezone=True))  # Last review timestamp (UTC)
    
    # === Legacy Columns (Deprecated - preserved for data integrity but not used) ===
    # do NOT use these in backend logic. Use fsrs_* instead.
    interval = db.Column(db.Integer, default=0)  # Current interval in minutes (Optional, can keep for history)
    repetitions = db.Column(db.Integer, default=0)  # Total review count
    
    # === Statistics ===
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    
    # === Mode-Specific Extended Data ===
    # Used for: Memrise (memory_level, session_reps), Course (completion_percentage)
    mode_data = db.Column(JSON, nullable=True)
    
    # === FSRS State Constants ===
    STATE_NEW = 0
    STATE_LEARNING = 1
    STATE_REVIEW = 2
    STATE_RELEARNING = 3
    
    # === Legacy Aliases (for backward compatibility) ===
    FSRS_STATE_NEW = STATE_NEW
    FSRS_STATE_LEARNING = STATE_LEARNING
    FSRS_STATE_REVIEW = STATE_REVIEW
    FSRS_STATE_RELEARNING = STATE_RELEARNING
    
    # === Mode Constants ===
    MODE_FLASHCARD = 'flashcard'
    MODE_QUIZ = 'quiz'
    MODE_MEMRISE = 'memrise'
    MODE_TYPING = 'typing'
    MODE_LISTENING = 'listening'
    MODE_COURSE = 'course'
    
    # === Relationships ===
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
        db.Index('ix_learning_progress_due', 'user_id', 'learning_mode', 'fsrs_due'),
        db.Index('ix_learning_progress_state', 'user_id', 'learning_mode', 'fsrs_state'),
        db.Index('ix_learning_progress_user_mode', 'user_id', 'learning_mode'),
    )
    
    # === Serialization ===
    def to_dict(self) -> dict:
        """Serialize progress to dictionary."""
        return {
            'progress_id': self.progress_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'learning_mode': self.learning_mode,
            'state': self.fsrs_state,
            'stability': self.fsrs_stability,
            'difficulty': self.fsrs_difficulty,
            'due': self.fsrs_due.isoformat() if self.fsrs_due else None,
            'last_review': self.fsrs_last_review.isoformat() if self.fsrs_last_review else None,
            'times_correct': self.times_correct,
            'times_incorrect': self.times_incorrect,
            'correct_streak': self.correct_streak,
        }
    
    @property
    def state_name(self) -> str:
        """Human-readable state name."""
        names = {
            self.STATE_NEW: 'Mới',
            self.STATE_LEARNING: 'Đang học',
            self.STATE_REVIEW: 'Ôn tập',
            self.STATE_RELEARNING: 'Học lại',
        }
        return names.get(self.fsrs_state, 'Unknown')
    
    # === Backward Compatibility Properties (Mapped to FSRS) ===
    
    @property
    def stability(self):
        """Deprecated alias for fsrs_stability."""
        return self.fsrs_stability
    
    @stability.setter
    def stability(self, value):
        self.fsrs_stability = value
        
    @property
    def difficulty(self):
        """Deprecated alias for fsrs_difficulty."""
        return self.fsrs_difficulty
    
    @difficulty.setter
    def difficulty(self, value):
        self.fsrs_difficulty = value
        
    @property
    def state(self):
        """Deprecated alias for fsrs_state."""
        return self.fsrs_state
    
    @state.setter
    def state(self, value):
        self.fsrs_state = value
        
    @property
    def due(self):
        """Deprecated alias for fsrs_due."""
        return self.fsrs_due
    
    @due.setter
    def due(self, value):
        self.fsrs_due = value
    
    @property
    def last_review(self):
        """Deprecated alias for fsrs_last_review."""
        return self.fsrs_last_review
    
    @last_review.setter
    def last_review(self, value):
        self.fsrs_last_review = value

    @property
    def easiness_factor(self):
        """Legacy alias - returns fsrs_stability for compatibility."""
        return self.fsrs_stability
    
    @easiness_factor.setter
    def easiness_factor(self, value):
        """Legacy setter - stores to fsrs_stability."""
        self.fsrs_stability = value
    
    # === Legacy/Supplementary Data ===
    legacy_mastery = db.Column(db.Float, nullable=True)  # Reserved for Course completion (0.0-1.0)
    
    @property
    def status(self) -> str:
        """Legacy status string mapping for backward compat (Getter)."""
        status_map = {
            self.STATE_NEW: 'new',
            self.STATE_LEARNING: 'learning',
            self.STATE_REVIEW: 'reviewing',
            self.STATE_RELEARNING: 'learning',
        }
        return status_map.get(self.fsrs_state, 'new')

    @status.setter
    def status(self, value: str) -> None:
        """Legacy setter - maps status string to fsrs_state."""
        status_map = {
            'new': self.STATE_NEW,
            'learning': self.STATE_LEARNING,
            'reviewing': self.STATE_REVIEW,
            'relearning': self.STATE_RELEARNING,
            'mastered': self.STATE_REVIEW, 
            'hard': self.STATE_REVIEW
        }
        self.fsrs_state = status_map.get(value, self.STATE_NEW)

    @property
    def mastery(self):
        """Legacy alias for legacy_mastery."""
        return self.legacy_mastery
    
    @mastery.setter
    def mastery(self, value):
        self.legacy_mastery = value

    # === Memrise Compatibility Properties ===
    @property
    def memory_level(self) -> int:
        """Get Memrise memory level from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('memory_level', 0)
        return 0
    
    @memory_level.setter
    def memory_level(self, value: int) -> None:
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['memory_level'] = value
    
    @property
    def completion_percentage(self) -> int:
        """Get course completion percentage from mode_data."""
        if self.mode_data and isinstance(self.mode_data, dict):
            return self.mode_data.get('completion_percentage', 0)
        return 0
    
    @completion_percentage.setter
    def completion_percentage(self, value: int) -> None:
        if self.mode_data is None:
            self.mode_data = {}
        self.mode_data['completion_percentage'] = value

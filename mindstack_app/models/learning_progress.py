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
    - fsrs_stability: Memory stability in days (S)
    - fsrs_difficulty: Item difficulty 1-10 (D)
    - fsrs_state: Card state (0:New, 1:Learning, 2:Review, 3:Relearning)
    
    Legacy SM-2 columns should NOT be used for scheduling logic.
    """
    
    __tablename__ = 'learning_progress'
    
    # === Primary Keys ===
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    # === Learning Mode Discriminator ===
    learning_mode = db.Column(db.String(20), nullable=False, index=True)
    
    # === FSRS-5 Core State (Algorithm Variables) ===
    # Prefix: fsrs_
    fsrs_stability = db.Column(db.Float, default=0.0)  # S - memory stability in days
    fsrs_difficulty = db.Column(db.Float, default=0.0)  # D - item difficulty (1-10, default 0 for new)
    fsrs_state = db.Column(db.Integer, default=0, index=True)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    
    # === Scheduling ===
    fsrs_due = db.Column(db.DateTime(timezone=True), index=True)  # Next review due time (UTC)
    fsrs_last_review = db.Column(db.DateTime(timezone=True))  # Last review timestamp (UTC)
    
    # === User History & Statistics (No Prefix) ===
    # Generic stats independent of algorithm
    lapses = db.Column(db.Integer, default=0)      # Times user forgot a mature card (Review->Relearning)
    repetitions = db.Column(db.Integer, default=0) # Total review count
    last_review_duration = db.Column(db.Integer, default=0) # Time taken for last review (ms)
    
    # === Display Only / Legacy Preserved ===
    # Renamed from 'interval' to avoid confusion with FSRS calculations
    current_interval = db.Column(db.Float, default=0.0)  # Display: "Review in X days"
    
    # === Statistics (Counters) ===
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
            'lapses': self.lapses,
            'repetitions': self.repetitions,
            'interval': self.current_interval,
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

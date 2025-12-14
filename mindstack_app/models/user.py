"""User and interaction related database models."""

from __future__ import annotations

from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from werkzeug.security import check_password_hash, generate_password_hash

from ..db_instance import db


class User(UserMixin, db.Model):
    """Application user model."""

    __tablename__ = 'users'

    ROLE_ADMIN = 'admin'
    ROLE_USER = 'user'
    ROLE_FREE = 'free'
    ROLE_ANONYMOUS = 'anonymous'
    ROLE_LABELS = {
        ROLE_ADMIN: 'Quản trị viên',
        ROLE_USER: 'Người dùng chuẩn',
        ROLE_FREE: 'Tài khoản miễn phí',
        ROLE_ANONYMOUS: 'Ẩn danh',
    }

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_role = db.Column(db.String(50), default=ROLE_FREE, nullable=False)
    total_score = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime(timezone=True))
    timezone = db.Column(db.String(50), default='UTC')
    telegram_chat_id = db.Column(db.String(100), nullable=True, unique=True)

    # --- DEPRECATED FIELDS (Moved to UserSession) ---
    current_flashcard_container_id = db.Column(
        db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True
    )
    current_quiz_container_id = db.Column(
        db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True
    )
    current_course_container_id = db.Column(
        db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True
    )
    current_flashcard_mode = db.Column(db.String(50), nullable=True)
    current_quiz_mode = db.Column(db.String(50), nullable=True)
    current_quiz_batch_size = db.Column(db.Integer, nullable=True)
    flashcard_button_count = db.Column(db.Integer, default=3)
    # ------------------------------------------------

    # New 1-to-1 relationship with UserSession
    session_state = db.relationship('UserSession', uselist=False, backref='user', cascade='all, delete-orphan')

    contributed_containers = db.relationship('ContainerContributor', backref='user', lazy=True)
    container_states = db.relationship(
        'UserContainerState', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    flashcard_progress = db.relationship(
        'FlashcardProgress', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    quiz_progress = db.relationship(
        'QuizProgress', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    course_progress = db.relationship(
        'CourseProgress', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    feedbacks = db.relationship(
        'UserFeedback', foreign_keys='UserFeedback.user_id', backref='reporter', lazy=True
    )
    resolved_feedbacks = db.relationship(
        'UserFeedback', foreign_keys='UserFeedback.resolved_by_id', backref='resolver', lazy=True
    )
    
    # Relationship to new ReviewLogs
    review_logs = db.relationship('ReviewLog', backref='user', lazy='dynamic')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class UserContainerState(db.Model):
    """Stores per-user settings for a specific learning container."""

    __tablename__ = 'user_container_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)

    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    last_accessed = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    container = db.relationship(
        'LearningContainer',
        backref=db.backref('user_states', cascade='all, delete-orphan'),
        lazy=True,
    )

    __table_args__ = (db.UniqueConstraint('user_id', 'container_id', name='_user_container_uc'),)

    def to_dict(self) -> dict[str, object]:
        return {
            'is_archived': self.is_archived,
            'is_favorite': self.is_favorite,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
        }


class UserSession(db.Model):
    """
    [NEW] Stores transient session state for a user.
    Separates 'Identity' (User table) from 'State' (This table).
    """
    __tablename__ = 'user_sessions'

    # 1-to-1 relationship: user_id is both PK and FK
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)

    # Active Context
    current_flashcard_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_quiz_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_course_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)

    # Preferences / Settings
    current_flashcard_mode = db.Column(db.String(50), default='basic')
    current_quiz_mode = db.Column(db.String(50), default='standard')
    current_quiz_batch_size = db.Column(db.Integer, default=10)
    flashcard_button_count = db.Column(db.Integer, default=3)
    
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FlashcardProgress(db.Model):
    """Study progress for flashcard items."""

    __tablename__ = 'flashcard_progress'

    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)

    due_time = db.Column(db.DateTime(timezone=True))
    easiness_factor = db.Column(db.Float, default=2.5)
    repetitions = db.Column(db.Integer, default=0)
    interval = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime(timezone=True))

    status = db.Column(db.String(50), default='new')
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    times_vague = db.Column(db.Integer, default=0)
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    vague_streak = db.Column(db.Integer, default=0)
    first_seen_timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # DEPRECATED: Data moved to ReviewLog table. Kept for legacy compatibility if needed.
    review_history = db.Column(JSON)

    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='_user_flashcard_uc'),)


class QuizProgress(db.Model):
    """Study progress for quiz items."""

    __tablename__ = 'quiz_progress'

    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)

    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(50), default='new')
    first_seen_timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    review_history = db.Column(JSON)

    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='_user_quiz_uc'),)


class CourseProgress(db.Model):
    """Study progress for course items."""

    __tablename__ = 'course_progress'

    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)

    completion_percentage = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='_user_course_uc'),)


class ScoreLog(db.Model):
    """History of score changes for a user."""

    __tablename__ = 'score_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=True)
    score_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    item_type = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'score_change': self.score_change,
            'amount': self.score_change,
            'reason': self.reason,
            'item_type': self.item_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class LearningGoal(db.Model):
    """Stores personalised learning goals for each user."""

    __tablename__ = 'learning_goals'

    goal_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False) # Legacy or specific identifier
    domain = db.Column(db.String(50), default='general', nullable=False) # general, flashcard, quiz
    scope = db.Column(db.String(50), default='global', nullable=False) # global, container
    reference_id = db.Column(db.Integer, nullable=True) # container_id if scope=container
    metric = db.Column(db.String(50), default='points', nullable=False) # points, reviewed, new, correct
    
    period = db.Column(db.String(20), nullable=False, default='daily')
    target_value = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    user = db.relationship(
        'User',
        backref=db.backref('learning_goals', lazy=True, cascade='all, delete-orphan'),
        lazy=True,
    )

    __table_args__ = (
        db.Index('ix_learning_goals_user_period', 'user_id', 'period'),
    )


class GoalDailyHistory(db.Model):
    """Daily snapshot of goal progress for history tracking."""
    
    __tablename__ = 'goal_daily_history'

    history_id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('learning_goals.goal_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # The date this record represents
    
    current_value = db.Column(db.Integer, default=0) # Value achieved on this date (or cumulative, depending on logic)
    target_value = db.Column(db.Integer, default=0)  # Snapshot of target
    is_met = db.Column(db.Boolean, default=False)
    
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    goal = db.relationship(
        'LearningGoal',
        backref=db.backref('history_logs', lazy='dynamic', cascade='all, delete-orphan'),
        lazy=True,
    )

    __table_args__ = (
        db.UniqueConstraint('goal_id', 'date', name='_goal_daily_uc'),
    )


class UserNote(db.Model):
    """Personal notes for specific learning items."""

    __tablename__ = 'user_notes'

    note_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class UserFeedback(db.Model):
    """Feedback reports tied to specific learning items."""

    __tablename__ = 'user_feedback'

    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='new')
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)

    item = db.relationship('LearningItem', backref='feedbacks', lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_feedbacks', lazy=True)


class ContainerContributor(db.Model):
    """Permissions granted to users for learning containers."""

    __tablename__ = 'container_contributors'

    contributor_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(
        db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    permission_level = db.Column(db.String(50), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (db.UniqueConstraint('container_id', 'user_id', name='_container_user_uc'),)


class ReviewLog(db.Model):
    """
    [NEW] Normalized table for storing granular review history.
    Replaces the JSON 'review_history' blob in FlashcardProgress.
    """
    __tablename__ = 'review_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    rating = db.Column(db.Integer, nullable=False) # e.g. 0-5 for Flashcards, 1/0 for Quiz
    duration_ms = db.Column(db.Integer, default=0) # Time spent thinking
    
    # Snapshot of SRS state AFTER the review
    interval = db.Column(db.Integer)
    easiness_factor = db.Column(db.Float)
    
    review_type = db.Column(db.String(20), default='flashcard') # 'flashcard' or 'quiz'

    item = db.relationship('LearningItem', backref='review_logs')
"""User and interaction related database models."""

from __future__ import annotations

from flask import url_for
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
    avatar_url = db.Column(db.String(255), nullable=True) # URL hoặc đường dẫn file avatar
    
    # JSON column to store user's last preferences/configurations
    last_preferences = db.Column(JSON, default=dict)

    def get_avatar_url(self):
        """Trả về URL avatar của người dùng hoặc ảnh mặc định."""
        if self.avatar_url:
            # Nếu là đường dẫn nội bộ, đảm bảo có tiền tố /static/ hoặc /uploads/
            if self.avatar_url.startswith(('http://', 'https://')):
                return self.avatar_url
            return url_for('static', filename=self.avatar_url)
        # Trả về mã màu hoặc avatar theo tên nếu không có ảnh
        return None

    # DEPRECATED COLUMNS REMOVED: 
    # - current_flashcard_container_id, current_quiz_container_id, current_course_container_id
    # - current_flashcard_mode, current_quiz_mode, current_quiz_batch_size, flashcard_button_count
    # These fields have been moved to UserSession table (see user_sessions)

    # New 1-to-1 relationship with UserSession
    session_state = db.relationship('UserSession', uselist=False, backref='user', cascade='all, delete-orphan')

    contributed_containers = db.relationship('ContainerContributor', backref='user', lazy=True)
    container_states = db.relationship(
        'UserContainerState', backref='user', lazy=True, cascade='all, delete-orphan'
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
    
    # --- Preference Helpers ---
    def get_preference(self, key: str, default=None):
        """Get a specific preference value."""
        if self.last_preferences is None:
            return default
        return self.last_preferences.get(key, default)
    
    def set_preference(self, key: str, value) -> None:
        """Set a specific preference value."""
        if self.last_preferences is None:
            self.last_preferences = {}
        self.last_preferences[key] = value
    
    def get_flashcard_button_count(self) -> int:
        """Get the last used flashcard button count (3, 4, or 6)."""
        return self.get_preference('flashcard_button_count', 4)
    
    def set_flashcard_button_count(self, count: int) -> None:
        """Set the flashcard button count preference."""
        if count in [3, 4, 6]:
            self.set_preference('flashcard_button_count', count)


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
    
    # [NEW] JSON column to store per-container user preferences
    # Schema: { 'flashcard': {...}, 'mcq': {...}, 'listening': {...}, 'typing': {...} }
    settings = db.Column(JSON, default=dict)

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

    __table_args__ = (
        db.Index('ix_score_logs_user_timestamp', 'user_id', 'timestamp'),
        db.Index('ix_score_logs_timestamp', 'timestamp'),
    )

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

    item = db.relationship('LearningItem', backref=db.backref('user_notes', cascade='all, delete-orphan'))


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
    Replaces the JSON 'review_history' blob in FlashcardProgress and QuizProgress.
    """
    __tablename__ = 'review_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    rating = db.Column(db.Integer, nullable=False)  # 1-4 for FSRS, 0/1 for Quiz
    
    # === FSRS Optimizer Data ===
    scheduled_days = db.Column(db.Float, default=0.0)  # Interval assigned (S)
    elapsed_days = db.Column(db.Float, default=0.0)    # Days since last review
    review_duration = db.Column(db.Integer, default=0) # Time taken (ms)
    state = db.Column(db.Integer, default=0)           # State BEFORE review (0-3)
    
    # === Snapshots (Optional but useful) ===
    fsrs_stability = db.Column(db.Float, default=0.0)
    fsrs_difficulty = db.Column(db.Float, default=0.0)
    
    review_type = db.Column(db.String(20), default='flashcard')  # 'flashcard', 'quiz'
    
    # Legacy / Quiz specific
    user_answer = db.Column(db.String(10))   # Quiz answer selection (A, B, C, D)
    is_correct = db.Column(db.Boolean)       # Was answer correct?
    score_change = db.Column(db.Integer)     # Points earned/lost
    
    # Context
    session_id = db.Column(db.Integer, db.ForeignKey('learning_sessions.session_id'), nullable=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    mode = db.Column(db.String(50), nullable=True)  # "new", "review", "difficult"
    streak_position = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.Index('ix_review_logs_user_item', 'user_id', 'item_id'),
        db.Index('ix_review_logs_user_timestamp', 'user_id', 'timestamp'),
        db.Index('ix_review_logs_timestamp', 'timestamp'),
        db.Index('ix_review_logs_session', 'session_id'),
        db.Index('ix_review_logs_container', 'container_id'),
    )

    item = db.relationship('LearningItem', backref=db.backref('review_logs', cascade='all, delete-orphan'))


class UserItemMarker(db.Model):
    """
    [NEW] Stores user-specific markers for learning items.
    Used for 'Difficult', 'Ignored', 'Favorite' status.
    """
    __tablename__ = 'user_item_markers'

    marker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    # Marker Type: 'difficult', 'ignored', 'favorite'
    marker_type = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', 'marker_type', name='_user_item_marker_uc'),
        db.Index('ix_user_item_markers_user_type', 'user_id', 'marker_type'),
    )

    item = db.relationship('LearningItem', backref=db.backref('user_markers', cascade='all, delete-orphan'))
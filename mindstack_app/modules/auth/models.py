from __future__ import annotations
from datetime import datetime, timezone
from flask import url_for
from flask_login import UserMixin
from sqlalchemy.types import JSON
from werkzeug.security import check_password_hash, generate_password_hash
from mindstack_app.core.extensions import db

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
    avatar_url = db.Column(db.String(255), nullable=True) 
    
    last_preferences = db.Column(JSON, default=dict)

    # --- Relationships (String Reference) ---
    session_state = db.relationship('UserSession', uselist=False, backref='user', cascade='all, delete-orphan')
    
    contributed_containers = db.relationship('ContainerContributor', backref='user', lazy=True)
    container_states = db.relationship(
        'UserContainerState', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    study_logs = db.relationship('StudyLog', backref='user', lazy='dynamic')

    def get_avatar_url(self):
        if self.avatar_url:
            if self.avatar_url.startswith(('http://', 'https://')):
                return self.avatar_url
            return url_for('media_uploads', filename=self.avatar_url)
        return None

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def get_preference(self, key: str, default=None):
        if self.last_preferences is None:
            return default
        return self.last_preferences.get(key, default)
    
    def set_preference(self, key: str, value) -> None:
        if self.last_preferences is None:
            self.last_preferences = {}
        self.last_preferences[key] = value
    
    def get_flashcard_button_count(self) -> int:
        return self.get_preference('flashcard_button_count', 4)
    
    def set_flashcard_button_count(self, count: int) -> None:
        if count in [3, 4, 6]:
            self.set_preference('flashcard_button_count', count)

class UserSession(db.Model):
    """Stores transient session state for a user."""
    __tablename__ = 'user_sessions'

    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    current_flashcard_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_quiz_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_course_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_flashcard_mode = db.Column(db.String(50), default='basic')
    current_quiz_mode = db.Column(db.String(50), default='standard')
    current_quiz_batch_size = db.Column(db.Integer, default=10)
    flashcard_button_count = db.Column(db.Integer, default=3)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

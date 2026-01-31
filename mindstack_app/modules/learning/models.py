from __future__ import annotations
from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from mindstack_app.core.extensions import db

class LearningContainer(db.Model):
    """Represents a collection of learning content (courses, flashcards, quizzes)."""
    __tablename__ = 'learning_containers'

    _MEDIA_TYPES = ('image', 'audio')

    container_id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_type = db.Column(db.String(50), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': container_type,
        'polymorphic_identity': 'BASE_CONTAINER'
    }
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(512), nullable=True)
    tags = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ai_prompt = db.Column(db.Text, nullable=True)
    ai_capabilities = db.Column(JSON, nullable=True)
    media_image_folder = db.Column(db.String(255), nullable=True)
    media_audio_folder = db.Column(db.String(255), nullable=True)
    
    settings = db.Column(JSON, nullable=True)

    creator = db.relationship(
        'User',
        backref='created_containers',
        foreign_keys=[creator_user_id],
        lazy=True,
    )
    contributors = db.relationship(
        'ContainerContributor',
        backref='container',
        lazy=True,
        cascade='all, delete-orphan',
    )
    items = db.relationship(
        'LearningItem',
        backref='container',
        lazy=True,
        cascade='all, delete-orphan',
    )

    @staticmethod
    def _normalize_capabilities(value: Any) -> Optional[list[str]]:
        if value is None: return None
        result: set[str] = set()
        if isinstance(value, str): value = [value]
        if isinstance(value, Iterable):
            for item in value:
                if isinstance(item, str) and item.strip(): result.add(item.strip())
        elif isinstance(value, Mapping):
            for key, enabled in value.items():
                if enabled and isinstance(key, str) and key.strip(): result.add(key.strip())
        else: return None
        return sorted(result) or None

    @staticmethod
    def _normalize_media_folder(value: Any) -> Optional[str]:
        if not value: return None
        normalized = str(value).strip().replace('\\', '/')
        return normalized.strip('/') or None

    def set_media_folders(self, media_mapping: Optional[Mapping[str, Any]]) -> None:
        if not isinstance(media_mapping, Mapping):
            self.media_image_folder = None
            self.media_audio_folder = None
            return
        self.media_image_folder = self._normalize_media_folder(media_mapping.get('image'))
        self.media_audio_folder = self._normalize_media_folder(media_mapping.get('audio'))

    @property
    def media_folders(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if self.media_image_folder: result['image'] = self.media_image_folder
        if self.media_audio_folder: result['audio'] = self.media_audio_folder
        return result

    def capability_flags(self) -> set[str]:
        normalized = self._normalize_capabilities(self.ai_capabilities)
        return set(normalized) if normalized else set()

    @property
    def ai_settings(self) -> Optional[dict[str, Any]]:
        data: dict[str, Any] = {}
        if self.ai_prompt: data['custom_prompt'] = self.ai_prompt
        if self.ai_capabilities: data['capabilities'] = list(self.ai_capabilities)
        media_data = self.media_folders
        if media_data: data['media_folders'] = media_data
        return data or None

    @ai_settings.setter
    def ai_settings(self, value: Optional[Mapping[str, Any]]) -> None:
        if value is None:
            self.ai_prompt = self.ai_capabilities = self.media_image_folder = self.media_audio_folder = None
            return
        if not isinstance(value, Mapping): raise TypeError('ai_settings must be a mapping or None')
        payload = dict(value)
        prompt = payload.pop('custom_prompt', None)
        self.ai_prompt = str(prompt).strip() if isinstance(prompt, str) else None
        self.ai_capabilities = self._normalize_capabilities(payload.pop('capabilities', None))
        media_payload = payload.pop('media_folders', None)
        if not isinstance(media_payload, Mapping):
            fallback = {}
            for mtype in self._MEDIA_TYPES:
                key = f'{mtype}_base_folder'
                if key in payload: fallback[mtype] = payload.pop(key)
            media_payload = fallback
        self.set_media_folders(media_payload)

class LearningGroup(db.Model):
    __tablename__ = 'learning_groups'
    group_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_type = db.Column(db.String(50), nullable=False)
    content = db.Column(JSON, nullable=False)

    container = db.relationship('LearningContainer', backref=db.backref('groups', lazy=True, cascade='all, delete-orphan'), lazy=True)

class LearningItem(db.Model):
    __tablename__ = 'learning_items'
    item_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('learning_groups.group_id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': item_type,
        'polymorphic_identity': 'BASE_ITEM'
    }
    content = db.Column(JSON, nullable=False)
    order_in_container = db.Column(db.Integer, default=0)
    ai_explanation = db.Column(db.Text, nullable=True)
    custom_data = db.Column(JSON, nullable=True)
    search_text = db.Column(db.Text, nullable=True)

    group = db.relationship('LearningGroup', backref=db.backref('items', lazy=True), lazy=True)
    
    __table_args__ = (db.Index('ix_learning_items_search_text', 'search_text'),)

    def update_search_text(self):
        if not self.content: return
        text_parts = []
        c = self.content
        if self.item_type == 'FLASHCARD':
            if c.get('front'): text_parts.append(str(c['front']))
            if c.get('back'): text_parts.append(str(c['back']))
        elif self.item_type == 'QUIZ_MCQ':
            if c.get('question'): text_parts.append(str(c['question']))
            if c.get('explanation'): text_parts.append(str(c['explanation']))
            options = c.get('options')
            if isinstance(options, dict): text_parts.extend([str(v) for v in options.values() if v])
        self.search_text = " ".join(text_parts).lower()

class UserContainerState(db.Model):
    __tablename__ = 'user_container_states'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    last_accessed = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    container = db.relationship('LearningContainer', backref=db.backref('user_states', cascade='all, delete-orphan'), lazy=True)
    settings = db.Column(JSON, default=dict)
    __table_args__ = (db.UniqueConstraint('user_id', 'container_id', name='_user_container_uc'),)

    def to_dict(self) -> dict[str, object]:
        return {
            'is_archived': self.is_archived,
            'is_favorite': self.is_favorite,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
        }

class ContainerContributor(db.Model):
    __tablename__ = 'container_contributors'
    contributor_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    permission_level = db.Column(db.String(50), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('container_id', 'user_id', name='_container_user_uc'),)

class ReviewLog(db.Model):
    __tablename__ = 'review_logs'
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    rating = db.Column(db.Integer, nullable=False)
    scheduled_days = db.Column(db.Float, default=0.0)
    elapsed_days = db.Column(db.Float, default=0.0)
    review_duration = db.Column(db.Integer, default=0)
    state = db.Column(db.Integer, default=0)
    fsrs_stability = db.Column(db.Float, default=0.0)
    fsrs_difficulty = db.Column(db.Float, default=0.0)
    review_type = db.Column(db.String(20), default='flashcard')
    user_answer = db.Column(db.String(10))
    is_correct = db.Column(db.Boolean)
    score_change = db.Column(db.Integer)
    session_id = db.Column(db.Integer, db.ForeignKey('learning_sessions.session_id'), nullable=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    mode = db.Column(db.String(50), nullable=True)
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
    __tablename__ = 'user_item_markers'
    marker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    marker_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', 'marker_type', name='_user_item_marker_uc'),
        db.Index('ix_user_item_markers_user_type', 'user_id', 'marker_type'),
    )
    item = db.relationship('LearningItem', backref=db.backref('user_markers', cascade='all, delete-orphan'))

class LearningProgress(db.Model):
    """Unified FSRS-5 progress tracking for all learning modes."""
    __tablename__ = 'learning_progress'
    
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    learning_mode = db.Column(db.String(20), nullable=False, index=True)
    fsrs_stability = db.Column(db.Float, default=0.0)
    fsrs_difficulty = db.Column(db.Float, default=0.0)
    fsrs_state = db.Column(db.Integer, default=0, index=True)
    fsrs_due = db.Column(db.DateTime(timezone=True), index=True)
    fsrs_last_review = db.Column(db.DateTime(timezone=True))
    first_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    lapses = db.Column(db.Integer, default=0)
    repetitions = db.Column(db.Integer, default=0)
    last_review_duration = db.Column(db.Integer, default=0)
    current_interval = db.Column(db.Float, default=0.0)
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    mode_data = db.Column(JSON, nullable=True)
    
    STATE_NEW = 0
    STATE_LEARNING = 1
    STATE_REVIEW = 2
    STATE_RELEARNING = 3
    MODE_FLASHCARD = 'flashcard'
    MODE_QUIZ = 'quiz'
    MODE_MEMRISE = 'memrise'
    MODE_TYPING = 'typing'
    MODE_LISTENING = 'listening'
    MODE_COURSE = 'course'

    user = db.relationship('User', backref=db.backref('learning_progress', lazy='dynamic', cascade='all, delete-orphan'), lazy=True)
    item = db.relationship('LearningItem', backref=db.backref('progress_records', lazy='dynamic', cascade='all, delete-orphan'), lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', 'learning_mode', name='uq_user_item_mode'),
        db.Index('ix_learning_progress_due', 'user_id', 'learning_mode', 'fsrs_due'),
        db.Index('ix_learning_progress_state', 'user_id', 'learning_mode', 'fsrs_state'),
        db.Index('ix_learning_progress_user_mode', 'user_id', 'learning_mode'),
        db.Index('ix_learning_progress_first_seen', 'user_id', 'first_seen'),
    )

    def to_dict(self) -> dict:
        return {
            'progress_id': self.progress_id, 'user_id': self.user_id, 'item_id': self.item_id,
            'learning_mode': self.learning_mode, 'state': self.fsrs_state,
            'stability': self.fsrs_stability, 'difficulty': self.fsrs_difficulty,
            'due': self.fsrs_due.isoformat() if self.fsrs_due else None,
            'last_review': self.fsrs_last_review.isoformat() if self.fsrs_last_review else None,
            'lapses': self.lapses, 'repetitions': self.repetitions,
            'interval': self.current_interval, 'times_correct': self.times_correct,
            'times_incorrect': self.times_incorrect, 'correct_streak': self.correct_streak,
        }

    @property
    def state_name(self) -> str:
        names = {self.STATE_NEW: 'Mới', self.STATE_LEARNING: 'Đang học', self.STATE_REVIEW: 'Ôn tập', self.STATE_RELEARNING: 'Học lại'}
        return names.get(self.fsrs_state, 'Unknown')

    @property
    def memory_level(self) -> int:
        return self.mode_data.get('memory_level', 0) if self.mode_data and isinstance(self.mode_data, dict) else 0
    @memory_level.setter
    def memory_level(self, value: int) -> None:
        if self.mode_data is None: self.mode_data = {}
        self.mode_data['memory_level'] = value
    @property
    def completion_percentage(self) -> int:
        return self.mode_data.get('completion_percentage', 0) if self.mode_data and isinstance(self.mode_data, dict) else 0
    @completion_percentage.setter
    def completion_percentage(self, value: int) -> None:
        if self.mode_data is None: self.mode_data = {}
        self.mode_data['completion_percentage'] = value

class LearningSession(db.Model):
    """Model for tracking learning sessions."""
    __tablename__ = 'learning_sessions'
    
    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    learning_mode = db.Column(db.String(50), nullable=False)
    mode_config_id = db.Column(db.String(50), nullable=False)
    set_id_data = db.Column(JSON, nullable=False)
    status = db.Column(db.String(20), default='active', index=True)
    total_items = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    vague_count = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    processed_item_ids = db.Column(JSON, default=list)
    start_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    last_activity = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True))

    user = db.relationship('User', backref=db.backref('learning_sessions', lazy='dynamic', cascade='all, delete-orphan'), lazy=True)

    def to_dict(self):
        return {
            'session_id': self.session_id, 'user_id': self.user_id, 'learning_mode': self.learning_mode,
            'mode_config_id': self.mode_config_id, 'set_id_data': self.set_id_data, 'status': self.status,
            'total_items': self.total_items, 'correct_count': self.correct_count,
            'incorrect_count': self.incorrect_count, 'vague_count': self.vague_count,
            'points_earned': self.points_earned, 'processed_item_ids': self.processed_item_ids or [],
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }

    @property
    def is_active(self):
        return self.status == 'active'
    @property
    def progress_percentage(self):
        if not self.total_items or self.total_items == 0: return 0
        processed_count = len(self.processed_item_ids) if self.processed_item_ids else 0
        return min(100, int((processed_count / self.total_items) * 100))

from sqlalchemy import event
@event.listens_for(LearningItem, 'before_insert')
@event.listens_for(LearningItem, 'before_update')
def clean_learning_item_content(mapper, connection, target):
    if target.content and isinstance(target.content, dict):
        keys_to_remove = [k for k in target.content.keys() if k.startswith('supports_')]
        if keys_to_remove:
            new_content = dict(target.content)
            for k in keys_to_remove: new_content.pop(k, None)
            target.content = new_content
"""Learning domain models and helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any, Dict, Optional

from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db


class LearningContainer(db.Model):
    """Represents a collection of learning content (courses, flashcards, quizzes)."""

    __tablename__ = 'learning_containers'

    _MEDIA_TYPES = ('image', 'audio')

    container_id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(512), nullable=True)
    tags = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    # Structured configuration columns replacing the legacy ai_settings blob
    ai_prompt = db.Column(db.Text, nullable=True)
    ai_capabilities = db.Column(JSON, nullable=True)
    media_image_folder = db.Column(db.String(255), nullable=True)
    media_audio_folder = db.Column(db.String(255), nullable=True)
    
    # Generic settings for container defaults (e.g. default MCQ pairs, etc.)
    # Structure: {'mcq': {'default_pairs': [...]}, 'typing': {...}, 'listening': {...}}
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

    # ------------------------------------------------------------------
    # Helpers for working with the structured configuration
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_capabilities(value: Any) -> Optional[list[str]]:
        """Return a sorted list of capability flags or ``None``."""

        if value is None:
            return None

        result: set[str] = set()

        if isinstance(value, str):
            value = [value]

        if isinstance(value, Iterable):
            for item in value:
                if isinstance(item, str) and item.strip():
                    result.add(item.strip())
        elif isinstance(value, Mapping):
            for key, enabled in value.items():
                if enabled and isinstance(key, str) and key.strip():
                    result.add(key.strip())
        else:
            return None

        return sorted(result) or None

    @staticmethod
    def _normalize_media_folder(value: Any) -> Optional[str]:
        if not value:
            return None

        normalized = str(value).strip().replace('\\', '/')
        normalized = normalized.strip('/')
        return normalized or None

    def set_media_folders(self, media_mapping: Optional[Mapping[str, Any]]) -> None:
        """Persist media folder configuration from a mapping."""

        if not isinstance(media_mapping, Mapping):
            self.media_image_folder = None
            self.media_audio_folder = None
            return

        image_folder = self._normalize_media_folder(media_mapping.get('image'))
        audio_folder = self._normalize_media_folder(media_mapping.get('audio'))

        self.media_image_folder = image_folder
        self.media_audio_folder = audio_folder

    @property
    def media_folders(self) -> dict[str, str]:
        """Return configured media folders as a mapping."""

        result: dict[str, str] = {}
        if self.media_image_folder:
            result['image'] = self.media_image_folder
        if self.media_audio_folder:
            result['audio'] = self.media_audio_folder
        return result

    def capability_flags(self) -> set[str]:
        """Return the set of configured capability flags."""

        normalized = self._normalize_capabilities(self.ai_capabilities)
        if normalized:
            return set(normalized)

        normalized = self._normalize_capabilities(self.ai_capabilities)
        if normalized:
            return set(normalized)

        return set()

    @property
    def ai_settings(self) -> Optional[dict[str, Any]]:
        """Expose a consolidated AI configuration mapping."""

        data: dict[str, Any] = {}

        if self.ai_prompt:
             data['custom_prompt'] = self.ai_prompt

        capabilities = self.ai_capabilities
        if capabilities:
            data['capabilities'] = list(capabilities)

        media_data = self.media_folders
        if media_data:
            data['media_folders'] = media_data

        return data or None

    @ai_settings.setter
    def ai_settings(self, value: Optional[Mapping[str, Any]]) -> None:
        if value is None:
            self.ai_prompt = None
            self.ai_capabilities = None
            self.media_image_folder = None
            self.media_audio_folder = None
            return

        if not isinstance(value, Mapping):
            raise TypeError('ai_settings must be a mapping or None')

        payload: MutableMapping[str, Any] = dict(value)

        prompt_candidate = payload.pop('custom_prompt', None)
        if isinstance(prompt_candidate, str):
            prompt_candidate = prompt_candidate.strip()
        self.ai_prompt = prompt_candidate or None

        capabilities_value = payload.pop('capabilities', None)
        self.ai_capabilities = self._normalize_capabilities(capabilities_value)

        media_payload = payload.pop('media_folders', None)
        if not isinstance(media_payload, Mapping):
            fallback_media: Dict[str, Any] = {}
            for media_type in self._MEDIA_TYPES:
                fallback_key = f'{media_type}_base_folder'
                if fallback_key in payload:
                    fallback_media[media_type] = payload.pop(fallback_key)
            media_payload = fallback_media
        self.set_media_folders(media_payload)


class LearningGroup(db.Model):
    """Represents a shared context for multiple learning items (e.g. a passage)."""

    __tablename__ = 'learning_groups'

    group_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(
        db.Integer,
        db.ForeignKey('learning_containers.container_id'),
        nullable=False,
    )
    group_type = db.Column(db.String(50), nullable=False)
    content = db.Column(JSON, nullable=False)

    container = db.relationship(
        'LearningContainer',
        backref=db.backref(
            'groups',
            lazy=True,
            cascade='all, delete-orphan',
        ),
        lazy=True,
    )


class LearningItem(db.Model):
    """Represents a single learning artefact."""

    __tablename__ = 'learning_items'

    item_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(
        db.Integer,
        db.ForeignKey('learning_containers.container_id'),
        nullable=False,
    )
    group_id = db.Column(db.Integer, db.ForeignKey('learning_groups.group_id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False)
    content = db.Column(JSON, nullable=False)
    order_in_container = db.Column(db.Integer, default=0)
    ai_explanation = db.Column(db.Text, nullable=True)
    
    # [NEW] Custom data column for user-defined fields from Excel import
    custom_data = db.Column(JSON, nullable=True)
    
    # [NEW] Optimized search column
    search_text = db.Column(db.Text, nullable=True)

    group = db.relationship(
        'LearningGroup',
        backref=db.backref('items', lazy=True),
        lazy=True,
    )
    
    __table_args__ = (
        db.Index('ix_learning_items_search_text', 'search_text'),
    )

    def update_search_text(self):
        """Generates plain text for searching from the JSON content."""
        if not self.content:
            return

        text_parts = []
        c = self.content
        
        if self.item_type == 'FLASHCARD':
            # Index front and back
            if c.get('front'): text_parts.append(str(c['front']))
            if c.get('back'): text_parts.append(str(c['back']))
        
        elif self.item_type == 'QUIZ_MCQ':
            # Index question, options and explanation
            if c.get('question'): text_parts.append(str(c['question']))
            if c.get('explanation'): text_parts.append(str(c['explanation']))
            options = c.get('options')
            if isinstance(options, dict):
                text_parts.extend([str(v) for v in options.values() if v])
        
        # Join and lowercase for easier searching
        self.search_text = " ".join(text_parts).lower()

from sqlalchemy import event

@event.listens_for(LearningItem, 'before_insert')
@event.listens_for(LearningItem, 'before_update')
def clean_learning_item_content(mapper, connection, target):
    if target.content and isinstance(target.content, dict):
        keys_to_remove = [k for k in target.content.keys() if k.startswith('supports_')]
        if keys_to_remove:
            new_content = dict(target.content)
            for k in keys_to_remove:
                new_content.pop(k, None)
            target.content = new_content


"""Site-wide settings model for admin configuration."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.sql import func

from ..db_instance import db


class SiteSettings(db.Model):
    """Key-value store for site-wide configuration settings.
    
    Used by admin to control global settings like active template versions,
    feature flags, and other configurable options.
    """

    __tablename__ = 'site_settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)

    # Relationship to track who made the change
    updater = db.relationship(
        'User',
        foreign_keys=[updated_by],
        lazy=True,
    )

    # Default template settings keys
    TEMPLATE_FLASHCARD_SESSION = 'template.flashcard.cardsession'
    TEMPLATE_FLASHCARD_SETUP = 'template.flashcard.setup'
    TEMPLATE_QUIZ_SESSION = 'template.quiz.session'
    TEMPLATE_QUIZ_BATTLE = 'template.quiz.battle'
    TEMPLATE_COLLAB_DASHBOARD = 'template.collab.dashboard'

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a setting value by key.
        
        Args:
            key: The setting key
            default: Default value if key not found
            
        Returns:
            The setting value or default
        """
        setting = cls.query.get(key)
        if setting is None:
            return default
        return setting.value

    @classmethod
    def set(cls, key: str, value: Any, description: str = None, user_id: int = None) -> 'SiteSettings':
        """Set or update a setting.
        
        Args:
            key: The setting key
            value: The value to store (will be JSON serialized)
            description: Optional description of the setting
            user_id: ID of user making the change
            
        Returns:
            The SiteSettings instance
        """
        setting = cls.query.get(key)
        if setting is None:
            setting = cls(key=key, value=value, description=description, updated_by=user_id)
            db.session.add(setting)
        else:
            setting.value = value
            if description is not None:
                setting.description = description
            if user_id is not None:
                setting.updated_by = user_id
        return setting

    @classmethod
    def get_template_version(cls, template_type: str) -> str:
        """Get active template version for a template type.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            
        Returns:
            Active version string (e.g., 'v2') or 'default'
        """
        key = f'template.{template_type}'
        return cls.get(key, 'default')

    @classmethod
    def set_template_version(cls, template_type: str, version: str, user_id: int = None) -> None:
        """Set active template version for a template type.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            version: Version to set (e.g., 'v2')
            user_id: ID of admin making the change
        """
        key = f'template.{template_type}'
        cls.set(key, version, f'Active template for {template_type}', user_id)

    def __repr__(self) -> str:
        return f'<SiteSettings {self.key}={self.value!r}>'

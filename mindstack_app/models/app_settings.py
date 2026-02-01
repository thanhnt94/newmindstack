"""Unified application settings model for all configuration."""

from __future__ import annotations

from typing import Any, List, Optional, Dict

from sqlalchemy.sql import func

from mindstack_app.core.extensions import db


class AppSettings(db.Model):
    """Unified key-value store for all application settings.
    
    Consolidates site_settings and system_settings into one table.
    """

    __tablename__ = 'app_settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    
    # Categorization
    category = db.Column(db.String(50), default='system')  # 'system', 'template', 'scoring', 'ai', 'path', 'srs'
    
    # Metadata
    data_type = db.Column(db.String(50), default='string')  # 'string', 'int', 'float', 'json', 'list'
    description = db.Column(db.Text)
    
    # Audit
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)

    # Relationship for audit
    updater = db.relationship('User', foreign_keys=[updated_by], lazy=True)

    # --- Helper Methods ---
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a setting value by key with code-level default fallback.
        
        Args:
            key: The setting key
            default: Manual fallback if not found in DB AND not found in core/defaults.py
            
        Returns:
            The setting value or default
        """
        setting = cls.query.get(key)
        
        # 1. Check Database
        if setting is not None and setting.value is not None:
            return setting.value
            
        # 2. Check Code-Level Defaults
        from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
        if key in DEFAULT_APP_CONFIGS:
            return DEFAULT_APP_CONFIGS[key]
            
        # 3. Fallback to manual default
        return default

    @classmethod
    def set(cls, key: str, value: Any, category: str = None, 
            data_type: str = None, description: str = None, 
            user_id: int = None) -> 'AppSettings':
        """Set or update a setting.
        
        Args:
            key: The setting key
            value: The value to store (will be JSON serialized)
            category: Category for grouping settings
            data_type: Type hint for parsing
            description: Optional description
            user_id: ID of user making the change
            
        Returns:
            The AppSettings instance
        """
        setting = cls.query.get(key)
        if setting is None:
            setting = cls(
                key=key, 
                value=value,
                category=category or 'system',
                data_type=data_type or 'string',
                description=description,
                updated_by=user_id
            )
            db.session.add(setting)
        else:
            setting.value = value
            if category is not None:
                setting.category = category
            if data_type is not None:
                setting.data_type = data_type
            if description is not None:
                setting.description = description
            if user_id is not None:
                setting.updated_by = user_id
        return setting

    @classmethod
    def get_by_category(cls, category: str) -> List['AppSettings']:
        """Get all settings in a category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of AppSettings in that category
        """
        return cls.query.filter_by(category=category).all()

    # --- Template-specific helpers (backward compatible) ---
    
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
        cls.set(key, version, category='template', 
                description=f'Active template for {template_type}', 
                user_id=user_id)

    def __repr__(self) -> str:
        return f'<AppSettings {self.key}={self.value!r}>'

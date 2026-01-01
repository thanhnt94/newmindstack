"""Template service for managing dynamic template loading based on admin settings."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class TemplateService:
    """Service for managing template paths with dynamic versioning support."""
    
    # Base configuration for supported template types and their relative paths
    # The system assumes structure: templates/{version}/{relative_path}
    TEMPLATE_CONFIG = {
        'dashboard': {
            'label': 'Dashboard (Bảng điều khiển)',
            'relative_path': 'pages/dashboard'
        },
        'landing': {
            'label': 'Landing Page (Trang chủ)',
            'relative_path': 'pages/landing'
        },
        'auth.login': {
            'label': 'Authentication (Đăng nhập/Đăng ký)',
            'relative_path': 'pages/auth'
        },
        'flashcard.cardsession': {
            'label': 'Flashcard Session',
            'relative_path': 'pages/learning/flashcard/session'
        },
        'flashcard.setup': {
            'label': 'Flashcard Setup (Chọn chế độ)',
            'relative_path': 'pages/learning/flashcard/setup'
        },
        'quiz.session': {
            'label': 'Quiz Session (Làm bài)',
            'relative_path': 'pages/learning/quiz/individual/session/default'
        },
        'quiz.setup': {
            'label': 'Quiz Setup (Chọn bộ câu hỏi)',
            'relative_path': 'pages/learning/quiz/individual/setup'
        },
        'quiz.battle': {
            'label': 'Quiz Battle (Đối kháng)',
            'relative_path': 'pages/learning/quiz/battle'
        },
        'collab.dashboard': {
            'label': 'Collab Dashboard (Học nhóm)',
            'relative_path': 'pages/learning/collab/default'
        },
        'vocabulary.dashboard': {
            'label': 'Vocabulary (Từ vựng)',
            'relative_path': 'pages/learning/vocabulary'
        },
        'course.dashboard': {
            'label': 'Course (Khóa học)',
            'relative_path': 'pages/learning/course'
        },
    }

    # Default version fallback
    DEFAULT_VERSION = 'v3'

    @classmethod
    def get_active_version(cls, template_type: str) -> str:
        """Get the active version for a template type from AppSettings or default."""
        from mindstack_app.models import AppSettings
        
        setting_key = f"template_version_{template_type}"
        # Try to get from runtime config first (cache), then DB
        # For now, we query DB or specific cache if implemented. 
        # Simpler: Query DB directly for low-traffic admin actions, or use AppSettings service wrapper
        # Using a simplified direct dictionary lookup if cached in app config, else fallback
        
        # In a real app, this should be cached. For now, defaulting to 'v3' 
        # unless explicitly overridden in settings.
        
        # TODO: Integrate with AppSettings service properly
        # For now, enforce v3 as verified working version
        return cls.DEFAULT_VERSION

    @classmethod
    def get_template_path(cls, template_type: str, filename: str = 'index.html') -> str:
        """Get full template path based on active version."""
        config = cls.TEMPLATE_CONFIG.get(template_type)
        if not config:
            # Fallback for unknown types
            return f'{template_type}/{filename}'
            
        version = cls.get_active_version(template_type)
        relative_path = config['relative_path']
        
        # Verify if path exists for this version, fallback to default if not?
        # For now, assume active version is valid.
        return f'{version}/{relative_path}/{filename}'

    @classmethod
    def get_template_base_path(cls, template_type: str) -> str:
        """Get base path directory for dynamic includes."""
        config = cls.TEMPLATE_CONFIG.get(template_type)
        if not config:
            return template_type
            
        version = cls.get_active_version(template_type)
        relative_path = config['relative_path']
        return f'{version}/{relative_path}'
    
    @classmethod
    def get_template_context(cls, template_type: str) -> Dict[str, Any]:
        """Get context variables for template rendering."""
        base_path = cls.get_template_base_path(template_type)
        version = cls.get_active_version(template_type)
        return {
            'template_base_path': base_path,
            'template_version': version,
        }

    @classmethod
    def list_available_templates(cls, template_type: str) -> List[str]:
        """Scan templates directory for available versions of this type."""
        config = cls.TEMPLATE_CONFIG.get(template_type)
        if not config:
            return [cls.DEFAULT_VERSION]
            
        relative_path = config['relative_path'].replace('/', os.sep)
        templates_root = os.path.join(current_app.root_path, 'templates')
        
        available_versions = []
        
        if not os.path.exists(templates_root):
            return [cls.DEFAULT_VERSION]

        # List top-level directories (v3, v4, etc.)
        for item in os.listdir(templates_root):
            version_path = os.path.join(templates_root, item)
            if os.path.isdir(version_path):
                # Check if this version supports the requested template type
                target_path = os.path.join(version_path, relative_path)
                if os.path.exists(target_path):
                    available_versions.append(item)
                    
        return sorted(available_versions) if available_versions else [cls.DEFAULT_VERSION]

    @classmethod
    def get_all_template_settings(cls) -> Dict[str, Dict[str, Any]]:
        """Get all template configurations for Admin UI."""
        settings = {}
        for type_key, config in cls.TEMPLATE_CONFIG.items():
            versions = cls.list_available_templates(type_key)
            active = cls.get_active_version(type_key)
            
            settings[type_key] = {
                'label': config['label'],
                'active': active,
                'options': versions
            }
        return settings

    @classmethod
    def set_active_template(cls, template_type: str, version: str, user_id: int = None) -> None:
        """Set the active version for a template type (Persist to DB)."""
        from mindstack_app.models import AppSettings, db
        
        if template_type not in cls.TEMPLATE_CONFIG:
            raise ValueError(f"Invalid template type: {template_type}")
            
        # Verify version exists (optional but good practice)
        available = cls.list_available_templates(template_type)
        if version not in available:
             # Allow setting it anyway in case of manual override, but warn log
             pass
             
        key = f"template_version_{template_type}"
        setting = AppSettings.query.get(key)
        if not setting:
            setting = AppSettings(key=key, value=version, category='template', data_type='string')
            db.session.add(setting)
        else:
            setting.value = version
            
        db.session.commit()


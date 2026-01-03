"""Template service for managing dynamic template loading based on admin settings."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class TemplateService:
    """Service for managing template paths. Enforced to V3."""
    
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
            'relative_path': 'pages/learning/vocabulary/flashcard/session'
        },
        'flashcard.setup': {
            'label': 'Flashcard Setup (Chọn chế độ)',
            'relative_path': 'pages/learning/collab/flashcard'
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
    def get_available_global_versions(cls) -> List[str]:
        """Scan templates directory for available global versions."""
        templates_root = os.path.join(current_app.root_path, 'templates')
        if not os.path.exists(templates_root):
            return [cls.DEFAULT_VERSION]
            
        versions = []
        for item in os.listdir(templates_root):
            if os.path.isdir(os.path.join(templates_root, item)) and item.startswith('v'):
                versions.append(item)
        
        return sorted(versions) if versions else [cls.DEFAULT_VERSION]

    @classmethod
    def get_active_version(cls, template_type: str = None) -> str:
        """Get the active GLOBAL version from AppSettings or default."""
        from mindstack_app.models import AppSettings
        
        # We now use a single global key for the entire site
        key = "global_template_version"
        
        # Try to get from runtime config first (if cached)
        # For now, simplistic DB query as per original design requirement
        try:
            setting = AppSettings.query.get(key)
            if setting and setting.value:
                return setting.value
        except Exception:
            # Fallback if DB not ready or error
            pass
            
        return cls.DEFAULT_VERSION

    @classmethod
    def set_active_global_version(cls, version: str) -> None:
        """Set the global template version."""
        from mindstack_app.models import AppSettings, db
        
        available = cls.get_available_global_versions()
        if version not in available:
            # Maybe raise error or warn, but let's allow it for now with a warning log if possible
            pass
            
        key = "global_template_version"
        setting = AppSettings.query.get(key)
        if not setting:
            setting = AppSettings(key=key, value=version, category='template', data_type='string', description='Global Interface Version')
            db.session.add(setting)
        else:
            setting.value = version
            
        db.session.commit()

    @classmethod
    def get_template_path(cls, template_type: str, filename: str = 'index.html') -> str:
        """Get full template path based on active global version."""
        config = cls.TEMPLATE_CONFIG.get(template_type)
        if not config:
            return f'{template_type}/{filename}'
            
        # Use global version
        version = cls.get_active_version()
        relative_path = config['relative_path']
        
        return f'{version}/{relative_path}/{filename}'

    @classmethod
    def get_template_base_path(cls, template_type: str) -> str:
        """Get base path directory for dynamic includes."""
        config = cls.TEMPLATE_CONFIG.get(template_type)
        if not config:
            return template_type
            
        version = cls.get_active_version()
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
    def get_all_template_settings(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get template configurations for Admin UI.
        Refactored to return a single 'Global System' setting instead of per-module.
        """
        versions = cls.get_available_global_versions()
        active = cls.get_active_version()
        
        # Return a single item dictionary representing the Global Theme
        return {
            'global_system': {
                'label': 'Giao diện Toàn hệ thống (Global Theme)',
                'active': active,
                'options': versions
            }
        }

    @classmethod
    def set_active_template(cls, template_type: str, version: str, user_id: int = None) -> None:
        """Legacy adapter: redirects to set_active_global_version."""
        # We ignore 'template_type' effectively, enforcing global switch
        cls.set_active_global_version(version)


"""Template service for managing dynamic template loading based on admin settings."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class TemplateService:
    """Service for managing template versions and paths.
    
    Provides methods to:
    - Get active template version from SiteSettings
    - List available template versions by scanning folders
    - Build template paths for rendering
    
    Includes caching to avoid DB queries on every request.
    """
    
    # Cache storage: {key: (value, timestamp)}
    _cache: Dict[str, Tuple[Any, float]] = {}
    _cache_ttl: int = 300  # 5 minutes
    
    # Template type to folder mapping
    TEMPLATE_MAPPING = {
        # Learning - Flashcard
        'flashcard.cardsession': 'flashcard/individual/cardsession',
        'flashcard.setup': 'flashcard/individual/setup',
        # Learning - Quiz
        'quiz.session': 'quiz/individual/session',
        'quiz.setup': 'quiz/individual/setup',
        'quiz.battle': 'quiz/battle',
        # Learning - Collab
        'collab.dashboard': 'collab',
        # Main Pages
        'dashboard': 'dashboard',
        'landing': 'landing',
        # Learning - Vocabulary
        'vocabulary.dashboard': 'vocabulary',
        'vocabulary.detail': 'vocabulary/detail',
        # Learning - Course
        'course.dashboard': 'course',
        'course.detail': 'course/detail',
        # Auth
        'auth.login': 'auth',
        # User Profile
        'user_profile': 'user_profile',
    }
    
    @classmethod
    def _get_from_cache(cls, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in cls._cache:
            value, timestamp = cls._cache[key]
            if time.time() - timestamp < cls._cache_ttl:
                return value
            del cls._cache[key]
        return None
    
    @classmethod
    def _set_cache(cls, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        cls._cache[key] = (value, time.time())
    
    @classmethod
    def clear_cache(cls, key: str = None) -> None:
        """Clear cache for a specific key or all cache."""
        if key:
            cls._cache.pop(key, None)
        else:
            cls._cache.clear()
    
    @classmethod
    def get_active_template(cls, template_type: str) -> str:
        """Get active template version for a template type.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            
        Returns:
            Active version string (e.g., 'v2') or 'default'
        """
        cache_key = f'template_version:{template_type}'
        cached = cls._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Import here to avoid circular imports
        from mindstack_app.models import SiteSettings
        
        version = SiteSettings.get_template_version(template_type)
        cls._set_cache(cache_key, version)
        return version
    
    @classmethod
    def set_active_template(cls, template_type: str, version: str, user_id: int = None) -> None:
        """Set active template version (admin only).
        
        Args:
            template_type: Template type key
            version: Version to set
            user_id: ID of admin making the change
        """
        from mindstack_app.models import SiteSettings, db
        
        SiteSettings.set_template_version(template_type, version, user_id)
        db.session.commit()
        
        # Clear cache for this template type
        cls.clear_cache(f'template_version:{template_type}')
    
    @classmethod
    def list_available_templates(cls, template_type: str) -> List[str]:
        """List available template versions by scanning the folder.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            
        Returns:
            List of version folder names (e.g., ['v1', 'v2', 'default'])
        """
        cache_key = f'template_list:{template_type}'
        cached = cls._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        folder_path = cls.TEMPLATE_MAPPING.get(template_type)
        if not folder_path:
            return ['default']
        
        # Build absolute path to template folder
        try:
            # Get the templates folder from Flask app
            # Templates are in modules/<module>/templates/<path>
            module_name = folder_path.split('/')[0]  # e.g., 'flashcard'
            
            # Find the module's template folder
            app = current_app._get_current_object()
            for blueprint_name, blueprint in app.blueprints.items():
                if module_name in blueprint_name and blueprint.template_folder:
                    base_path = os.path.dirname(blueprint.template_folder)
                    full_path = os.path.join(base_path, 'templates', folder_path)
                    
                    if os.path.isdir(full_path):
                        versions = [
                            d for d in os.listdir(full_path)
                            if os.path.isdir(os.path.join(full_path, d))
                            and not d.startswith('_')
                            and not d.startswith('.')
                        ]
                        if versions:
                            versions.sort()
                            cls._set_cache(cache_key, versions)
                            return versions
        except Exception as e:
            current_app.logger.warning(f"Error listing templates for {template_type}: {e}")
        
        return ['default']
    
    @classmethod
    def get_template_path(cls, template_type: str, filename: str = 'index.html') -> str:
        """Get full template path for rendering.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            filename: Template filename (default: 'index.html')
            
        Returns:
            Full template path (e.g., 'flashcard/individual/cardsession/v2/index.html')
        """
        folder_path = cls.TEMPLATE_MAPPING.get(template_type)
        if not folder_path:
            raise ValueError(f"Unknown template type: {template_type}")
        
        version = cls.get_active_template(template_type)
        
        # Build path: folder_path/version/filename
        return f'{folder_path}/{version}/{filename}'
    
    @classmethod
    def get_all_template_settings(cls) -> Dict[str, Dict[str, Any]]:
        """Get all template types with their active versions and available options.
        
        Returns:
            Dict of template_type -> {active: str, options: List[str], label: str}
        """
        result = {}
        labels = {
            # Learning - Flashcard
            'flashcard.cardsession': 'Flashcard - Phiên học',
            'flashcard.setup': 'Flashcard - Thiết lập',
            # Learning - Quiz
            'quiz.session': 'Quiz - Phiên học',
            'quiz.setup': 'Quiz - Thiết lập',
            'quiz.battle': 'Quiz - Đấu trường',
            # Learning - Collab
            'collab.dashboard': 'Học nhóm',
            # Main Pages
            'dashboard': 'Dashboard chính',
            'landing': 'Trang chủ (Landing)',
            # Learning - Vocabulary
            'vocabulary.dashboard': 'Từ vựng - Dashboard',
            'vocabulary.detail': 'Từ vựng - Chi tiết',
            # Learning - Course
            'course.dashboard': 'Khóa học - Dashboard',
            'course.detail': 'Khóa học - Chi tiết',
            # Auth
            'auth.login': 'Đăng nhập/Đăng ký',
            # User Profile
            'user_profile': 'Hồ sơ người dùng',
        }
        
        for template_type in cls.TEMPLATE_MAPPING.keys():
            result[template_type] = {
                'active': cls.get_active_template(template_type),
                'options': cls.list_available_templates(template_type),
                'label': labels.get(template_type, template_type),
            }
        
        return result
    
    @classmethod
    def get_template_base_path(cls, template_type: str) -> str:
        """Get base path for dynamic includes in templates.
        
        Args:
            template_type: Template type key (e.g., 'flashcard.cardsession')
            
        Returns:
            Base path string (e.g., 'flashcard/individual/cardsession/v2')
        """
        folder_path = cls.TEMPLATE_MAPPING.get(template_type)
        if not folder_path:
            raise ValueError(f"Unknown template type: {template_type}")
        
        version = cls.get_active_template(template_type)
        return f'{folder_path}/{version}'
    
    @classmethod
    def get_template_context(cls, template_type: str) -> Dict[str, Any]:
        """Get context variables for template rendering.
        
        Pass this to render_template() to enable dynamic includes.
        
        Args:
            template_type: Template type key
            
        Returns:
            Dict with template_base_path and other useful variables
        """
        base_path = cls.get_template_base_path(template_type)
        version = cls.get_active_template(template_type)
        
        return {
            'template_base_path': base_path,
            'template_version': version,
        }


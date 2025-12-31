from __future__ import annotations

"""Template service for managing dynamic template loading based on admin settings."""

import os
import time
from typing import Any, Dict, List, Optional

from flask import current_app


class TemplateService:
    """Service for managing the global template version.
    
    Provides methods to:
    - Get active global template version (default: 'v1').
    - List available global versions (scans root templates folder).
    
    Includes caching to avoid DB queries on every request.
    """
    
    # Cache storage: {key: (value, timestamp)}
    _cache: Dict[str, tuple[Any, float]] = {}
    _cache_ttl: int = 300  # 5 minutes
    
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
    def clear_cache(cls) -> None:
        """Clear all cache."""
        cls._cache.clear()
    
    @classmethod
    def get_active_global_version(cls) -> str:
        """Get active global template version.
        
        Returns:
            Active version string (e.g., 'v1')
        """
        cache_key = 'global_template_version'
        cached = cls._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Import here to avoid circular imports
        from mindstack_app.models import AppSettings
        
        # We reuse the AppSettings mechanism but with a fixed key
        # If not set, default to 'v1'
        setting = AppSettings.query.get('global_template_version')
        version = setting.value if setting else 'v1'
        
        cls._set_cache(cache_key, version)
        return version
    
    @classmethod
    def set_active_global_version(cls, version: str, user_id: int = None) -> None:
        """Set active global template version (admin only).
        
        Args:
            version: Version to set
            user_id: ID of admin making the change
        """
        from mindstack_app.models import AppSettings, db
        from sqlalchemy.orm.attributes import flag_modified
        
        setting = AppSettings.query.get('global_template_version')
        if not setting:
            setting = AppSettings(
                key='global_template_version',
                value=version,
                category='template',
                data_type='string',
                description='Global template version for the site'
            )
            db.session.add(setting)
        else:
            setting.value = version
            flag_modified(setting, 'value')
            
        db.session.commit()
        
        # Clear cache
        cls.clear_cache()
    
    @classmethod
    def list_available_versions(cls) -> List[str]:
        """List available global template versions root templates folder.
        
        Returns:
            List of version folder names (e.g., ['v1', 'v2'])
        """
        cache_key = 'available_versions'
        cached = cls._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Root templates folder is configured in app
            app = current_app._get_current_object()
            
            # app.template_folder should be absolute or relative to root path
            # But Flask stores it relative if passed that way? 
            # safe assumption: os.path.join(app.root_path, app.template_folder)
            
            template_folder = app.template_folder
            if not os.path.isabs(template_folder):
                template_folder = os.path.join(app.root_path, template_folder)
                
            if os.path.isdir(template_folder):
                versions = [
                    d for d in os.listdir(template_folder)
                    if os.path.isdir(os.path.join(template_folder, d))
                    and not d.startswith('_')
                    and not d.startswith('.')
                    # Heuristic: version folders usually start with 'v' or are 'default'
                    # But we trust any folder in 'templates/' is a version root now.
                ]
                if versions:
                    versions.sort()
                    cls._set_cache(cache_key, versions)
                    return versions
        except Exception as e:
            current_app.logger.warning(f"Error listing versions: {e}")
        
        return ['v1']

    @classmethod
    def get_template_context(cls, module_name: str) -> Dict[str, Any]:
        """Get template context for a specific module.
        
        Args:
            module_name: Name of the module (e.g., 'flashcard.cardsession')
            
        Returns:
            Dictionary containing 'template_base_path' and 'template_version'
        """
        # Default logic for now
        version = cls.get_active_global_version()
        
        # Map module names to paths
        # This is a temporary hardcoded map until we have a better registry
        path_map = {
            'flashcard.cardsession': 'pages/flashcard/individual/individual/cardsession'
        }
        
        base_path = path_map.get(module_name)
        if not base_path:
             # Fallback generic path construction if not in map
             # e.g. flashcard.cardsession -> pages/flashcard/cardsession/default
             parts = module_name.split('.')
             if len(parts) > 1:
                 base_path = f"pages/{parts[0]}/{parts[1]}/default"
             else:
                 base_path = f"pages/{parts[0]}/default"

        return {
            'template_base_path': base_path,
            'template_version': version
        }



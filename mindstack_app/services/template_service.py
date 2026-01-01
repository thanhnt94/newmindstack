"""Template service for managing dynamic template loading based on admin settings."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class TemplateService:
    """Service for managing template paths.
    
    SIMPLIFIED FOR V3 MIGRATION:
    This service now hardcodes paths to the new V3 structure where applicable,
    or defaults to V3 for standardized modules.
    """
    
    # Mapping old template keys to new V3 paths
    V3_MAPPING = {
        'flashcard.cardsession': 'v3/pages/learning/flashcard/session',
        'flashcard.setup': 'v3/pages/learning/flashcard/setup',
        'quiz.session': 'v3/pages/learning/quiz/individual/session/default',
        'quiz.setup': 'v3/pages/learning/quiz/individual/setup',
        'quiz.battle': 'v3/pages/learning/quiz/battle',
        'collab.dashboard': 'v3/pages/learning/collab/default',
        'dashboard': 'v3/pages/dashboard',
        'landing': 'v3/pages/landing',
        'vocabulary.dashboard': 'v3/pages/learning/vocabulary',
        'course.dashboard': 'v3/pages/learning/course',
        'auth.login': 'v3/pages/auth',
    }
    
    @classmethod
    def get_template_path(cls, template_type: str, filename: str = 'index.html') -> str:
        """Get full template path (V3 enforced)."""
        base_path = cls.V3_MAPPING.get(template_type)
        if base_path:
            return f'{base_path}/{filename}'
            
        # Fallback for unknown types (though most should be covered)
        return f'{template_type}/{filename}'

    @classmethod
    def get_template_base_path(cls, template_type: str) -> str:
        """Get base path for dynamic includes (V3 enforced)."""
        return cls.V3_MAPPING.get(template_type, template_type)
    
    @classmethod
    def get_template_context(cls, template_type: str) -> Dict[str, Any]:
        """Get context variables (V3 enforced)."""
        base_path = cls.get_template_base_path(template_type)
        return {
            'template_base_path': base_path,
            'template_version': 'v3',
        }

    # Deprecated/Stubbed methods to prevent crashes
    @classmethod
    def clear_cache(cls, key: str = None) -> None: pass
    
    @classmethod
    def get_active_template(cls, template_type: str) -> str: return 'v3'

    @classmethod
    def set_active_template(cls, template_type: str, version: str, user_id: int = None) -> None: pass

    @classmethod
    def list_available_templates(cls, template_type: str) -> List[str]: return ['v3']

    @classmethod
    def get_all_template_settings(cls) -> Dict[str, Dict[str, Any]]: return {}


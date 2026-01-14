"""
Flashcard Configuration Service

Provides centralized configuration for Flashcard (Vocabulary) system.
Retrieves settings from AppSettings with fallback to defaults.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from functools import lru_cache
import json

from flask import current_app

from ..models import AppSettings, db


class FlashcardConfigService:
    """Service for managing Flashcard / Vocabulary configuration."""

    # Category for all Flashcard settings in AppSettings
    CATEGORY = 'flashcard_config'

    # Default values - used when no DB config exists
    DEFAULTS: Dict[str, Any] = {
        # === Upload Limits ===
        'FLASHCARD_UPLOAD_MAX_SIZE_MB': 10,
        'FLASHCARD_ALLOWED_EXTENSIONS': ['.xlsx'],

        # === Excel Parsing ===
        'FLASHCARD_EXCEL_SHEET_NAMES': {'data': 'Data', 'info': 'Info'},
        'FLASHCARD_REQUIRED_COLUMNS': ['front', 'back'],
        
        # === Limits ===
        'FLASHCARD_FILENAME_MAX_LENGTH': 150,

        # === Column Definitions ===
        # Standard columns that map directly to item content or file paths
        'FLASHCARD_STANDARD_COLUMNS': [
           'question', 'pre_question_text',  # Legacy/Quiz-like compatibility if needed
           'front', 'back',
           'front_audio_content', 'back_audio_content',
           'front_img', 'back_img', 'front_audio_url', 'back_audio_url'
        ],
        
        # System columns managed by logic
        'FLASHCARD_SYSTEM_COLUMNS': ['item_id', 'order_in_container', 'action'],

        # Columns for AI generation
        'FLASHCARD_AI_COLUMNS': ['ai_explanation'],
    }

    # Setting descriptions for UI - Vietnamese
    DESCRIPTIONS: Dict[str, str] = {
        'FLASHCARD_UPLOAD_MAX_SIZE_MB': 'Dung lượng tối đa cho file Excel upload (MB). Mặc định 10MB.',
        'FLASHCARD_ALLOWED_EXTENSIONS': 'Danh sách đuôi file cho phép upload (VD: .xlsx).',
        'FLASHCARD_EXCEL_SHEET_NAMES': 'Tên các sheet trong file Excel (Data, Info).',
        'FLASHCARD_REQUIRED_COLUMNS': 'Các cột bắt buộc phải có trong sheet Data.',
        'FLASHCARD_FILENAME_MAX_LENGTH': 'Độ dài tối đa của tên file khi xuất ra.',
        'FLASHCARD_STANDARD_COLUMNS': 'Danh sách các cột dữ liệu chuẩn (front, back, media...).',
        'FLASHCARD_SYSTEM_COLUMNS': 'Các cột hệ thống (ID, thứ tự, hành động).',
        'FLASHCARD_AI_COLUMNS': 'Các cột chứa nội dung do AI tạo (giải thích).',
    }

    # Data types for form rendering
    DATA_TYPES: Dict[str, str] = {
        'FLASHCARD_UPLOAD_MAX_SIZE_MB': 'int',
        'FLASHCARD_ALLOWED_EXTENSIONS': 'list',  # Render as comma-separated string
        'FLASHCARD_EXCEL_SHEET_NAMES': 'json',
        'FLASHCARD_REQUIRED_COLUMNS': 'list',
        'FLASHCARD_FILENAME_MAX_LENGTH': 'int',
        'FLASHCARD_STANDARD_COLUMNS': 'list',
        'FLASHCARD_SYSTEM_COLUMNS': 'list',
        'FLASHCARD_AI_COLUMNS': 'list',
    }

    # Group settings for UI display
    GROUPS: Dict[str, Dict[str, Any]] = {
        'limits': {
            'label': 'Giới hạn Upload',
            'icon': 'fas fa-cloud-upload-alt',
            'keys': [
                'FLASHCARD_UPLOAD_MAX_SIZE_MB',
                'FLASHCARD_ALLOWED_EXTENSIONS',
                'FLASHCARD_FILENAME_MAX_LENGTH',
            ],
        },
        'excel_structure': {
            'label': 'Cấu trúc Excel',
            'icon': 'fas fa-table',
            'keys': [
                'FLASHCARD_EXCEL_SHEET_NAMES',
                'FLASHCARD_REQUIRED_COLUMNS',
            ],
        },
        'columns': {
            'label': 'Định nghĩa Cột',
            'icon': 'fas fa-columns',
            'keys': [
                'FLASHCARD_STANDARD_COLUMNS',
                'FLASHCARD_SYSTEM_COLUMNS',
                'FLASHCARD_AI_COLUMNS',
            ],
        },
    }

    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False

    @classmethod
    def _ensure_cache(cls) -> None:
        """Load all settings into cache if not already loaded."""
        if cls._cache_loaded:
            return

        try:
            settings = AppSettings.get_by_category(cls.CATEGORY)
            for setting in settings:
                cls._cache[setting.key] = setting.value
            cls._cache_loaded = True
        except Exception as e:
            current_app.logger.debug(f"Could not load Flashcard config from DB: {e}")

    @classmethod
    def invalidate_cache(cls) -> None:
        """Clear the config cache."""
        cls._cache.clear()
        cls._cache_loaded = False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        cls._ensure_cache()
        if key in cls._cache:
            return cls._cache[key]
        if key in cls.DEFAULTS:
            return cls.DEFAULTS[key]
        return default

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all settings with current values."""
        cls._ensure_cache()
        result = {}
        for key, default_value in cls.DEFAULTS.items():
            result[key] = cls._cache.get(key, default_value)
        return result

    @classmethod
    def get_grouped(cls) -> Dict[str, Dict[str, Any]]:
        """Get settings grouped for UI display."""
        all_settings = cls.get_all()
        grouped = {}

        for group_key, group_info in cls.GROUPS.items():
            grouped[group_key] = {
                'label': group_info['label'],
                'icon': group_info['icon'],
                'settings': [],
            }
            for setting_key in group_info['keys']:
                grouped[group_key]['settings'].append({
                    'key': setting_key,
                    'value': all_settings.get(setting_key),
                    'default': cls.DEFAULTS.get(setting_key),
                    'description': cls.DESCRIPTIONS.get(setting_key, ''),
                    'data_type': cls.DATA_TYPES.get(setting_key, 'string'),
                })

        return grouped

    @classmethod
    def set(cls, key: str, value: Any, user_id: int = None) -> None:
        """Save a configuration value to DB."""
        if key not in cls.DEFAULTS:
            # We enforce keys must be known, unless we want to allow dynamic keys
            pass 

        AppSettings.set(
            key=key,
            value=value,
            category=cls.CATEGORY,
            data_type=cls.DATA_TYPES.get(key, 'string'),
            description=cls.DESCRIPTIONS.get(key, ''),
            user_id=user_id,
        )
        cls._cache[key] = value

    @classmethod
    def save_all(cls, settings: Dict[str, Any], user_id: int = None) -> None:
        """Save multiple settings at once."""
        for key, value in settings.items():
            if key in cls.DEFAULTS:
                cls.set(key, value, user_id)
        
        db.session.commit()
        cls.invalidate_cache()

    @classmethod
    def reset_to_defaults(cls, user_id: int = None) -> None:
        """Reset all settings to default values."""
        for key, value in cls.DEFAULTS.items():
            cls.set(key, value, user_id)
        
        db.session.commit()
        cls.invalidate_cache()

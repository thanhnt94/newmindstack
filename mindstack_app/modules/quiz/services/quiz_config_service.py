"""
Quiz Configuration Service

Provides centralized configuration for Quiz system, analogous to FSRSSettingsService.
Retrieves settings from AppSettings with fallback to defaults.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from flask import current_app
from mindstack_app.models import AppSettings, db

class QuizConfigService:
    """Service for managing Quiz configuration."""

    CATEGORY = 'quiz_config'

    DEFAULTS: Dict[str, Any] = {
        # === Upload Rules ===
        'QUIZ_UPLOAD_MAX_SIZE_MB': 10,
        'QUIZ_ALLOWED_EXTENSIONS': ['.xlsx'],
        'QUIZ_FILENAME_MAX_LENGTH': 150,
        
        # === Excel Structure ===
        'QUIZ_EXCEL_SHEET_NAMES': {
            'data': 'Data', 
            'info': 'Info', 
            'readme': 'ReadMe'
        },
        'QUIZ_REQUIRED_COLUMNS': [
            'option_a', 
            'option_b', 
            'correct_answer_text'
        ],
        
        # === Column Definitions ===
        # These are the "Standard" columns known to the system.
        # Any column in Data sheet NOT in this list (and not System/AI) is considered Custom.
        'QUIZ_STANDARD_COLUMNS': [
            'question',
            'option_a', 'option_b', 'option_c', 'option_d',
            'correct_answer_text',
            'explanation',
            'question_image_file',
            'question_audio_file',
            'tags',
            # Group fields
            'group_id', 'group_text', 'group_image', 'group_audio', 'group_title'
        ],
        
        'QUIZ_AI_COLUMNS': [
            'ai_generated', 
            'ai_checked'
        ],
        
        'QUIZ_SYSTEM_COLUMNS': [
            'item_id', 
            'action', 
            'error'
        ],
        
        # === Import Logic ===
        'QUIZ_IMPORT_BATCH_SIZE': 100,
    }

    DESCRIPTIONS: Dict[str, str] = {
        'QUIZ_UPLOAD_MAX_SIZE_MB': '''Kích thước tối đa cho file Excel tải lên (MB).
Mặc định: 10 MB.''',
        
        'QUIZ_ALLOWED_EXTENSIONS': '''Danh sách các đuôi file cho phép tải lên.
Mặc định: [".xlsx"].''',

        'QUIZ_FILENAME_MAX_LENGTH': '''Độ dài tối đa của tên file khi xuất ra (ký tự).
Mặc định: 150.''',

        'QUIZ_EXCEL_SHEET_NAMES': '''Tên các sheet bắt buộc trong file Excel.
Mặc định: {"data": "Data", "info": "Info", "readme": "ReadMe"}.''',

        'QUIZ_REQUIRED_COLUMNS': '''Danh sách các cột BẮT BUỘC phải có trong sheet Data.
Nếu thiếu các cột này, file sẽ bị báo lỗi.
Mặc định: option_a, option_b, correct_answer_text.''',

        'QUIZ_STANDARD_COLUMNS': '''Danh sách các cột chuẩn (Standard) mà hệ thống nhận diện.
Bất kỳ cột nào không nằm trong danh sách này (và không phải System/AI) sẽ được coi là "Custom Data".''',

        'QUIZ_AI_COLUMNS': '''Các cột dành riêng cho AI sinh nội dung.''',

        'QUIZ_SYSTEM_COLUMNS': '''Các cột hệ thống dùng để xử lý logic (ID, hành động, lỗi).''',
        
        'QUIZ_IMPORT_BATCH_SIZE': '''Số lượng câu hỏi xử lý trong mỗi batch khi import (để tối ưu hiệu năng).''',
    }

    DATA_TYPES: Dict[str, str] = {
        'QUIZ_UPLOAD_MAX_SIZE_MB': 'int',
        'QUIZ_ALLOWED_EXTENSIONS': 'json',
        'QUIZ_FILENAME_MAX_LENGTH': 'int',
        'QUIZ_EXCEL_SHEET_NAMES': 'json',
        'QUIZ_REQUIRED_COLUMNS': 'json',
        'QUIZ_STANDARD_COLUMNS': 'json',
        'QUIZ_AI_COLUMNS': 'json',
        'QUIZ_SYSTEM_COLUMNS': 'json',
        'QUIZ_IMPORT_BATCH_SIZE': 'int',
    }

    GROUPS: Dict[str, Dict[str, Any]] = {
        'files': {
            'label': 'Quy tắc File & Upload',
            'icon': 'fas fa-file-upload',
            'keys': [
                'QUIZ_UPLOAD_MAX_SIZE_MB',
                'QUIZ_ALLOWED_EXTENSIONS',
                'QUIZ_FILENAME_MAX_LENGTH',
                'QUIZ_IMPORT_BATCH_SIZE',
            ]
        },
        'structure': {
            'label': 'Cấu trúc Excel',
            'icon': 'fas fa-table',
            'keys': [
                'QUIZ_EXCEL_SHEET_NAMES',
                'QUIZ_REQUIRED_COLUMNS',
            ]
        },
        'columns': {
            'label': 'Định nghĩa Cột',
            'icon': 'fas fa-columns',
            'keys': [
                'QUIZ_STANDARD_COLUMNS',
                'QUIZ_AI_COLUMNS',
                'QUIZ_SYSTEM_COLUMNS',
            ]
        }
    }

    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False

    @classmethod
    def _ensure_cache(cls) -> None:
        if cls._cache_loaded:
            return
        try:
            settings = AppSettings.get_by_category(cls.CATEGORY)
            for setting in settings:
                cls._cache[setting.key] = setting.value
            cls._cache_loaded = True
        except Exception as e:
            current_app.logger.debug(f"Could not load Quiz config from DB: {e}")

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache.clear()
        cls._cache_loaded = False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        cls._ensure_cache()
        if key in cls._cache:
            return cls._cache[key]
        if key in cls.DEFAULTS:
            return cls.DEFAULTS[key]
        return default

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        cls._ensure_cache()
        result = {}
        for key, default_value in cls.DEFAULTS.items():
            result[key] = cls._cache.get(key, default_value)
        return result

    @classmethod
    def get_grouped(cls) -> Dict[str, Dict[str, Any]]:
        all_settings = cls.get_all()
        grouped = {}
        for group_key, group_info in cls.GROUPS.items():
            grouped[group_key] = {
                'label': group_info['label'],
                'icon': group_info['icon'],
                'settings': []
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
        if key not in cls.DEFAULTS:
            raise ValueError(f"Unknown Quiz setting key: {key}")

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
        for key, value in settings.items():
            if key in cls.DEFAULTS:
                cls.set(key, value, user_id)
        db.session.commit()
        cls.invalidate_cache()

    @classmethod
    def reset_to_defaults(cls, user_id: int = None) -> None:
        for key, value in cls.DEFAULTS.items():
            cls.set(key, value, user_id)
        db.session.commit()
        cls.invalidate_cache()

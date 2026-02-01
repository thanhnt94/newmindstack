# File: mindstack_app/modules/fsrs/services/settings_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from flask import current_app
from mindstack_app.models import AppSettings, db
from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
from ..config import FSRSDefaultConfig

class FSRSSettingsService:
    """Service for managing FSRS configuration."""

    CATEGORY = 'srs'

    DEFAULTS: Dict[str, Any] = {
        'HARD_ITEM_MIN_INCORRECT_STREAK': DEFAULT_APP_CONFIGS.get('HARD_ITEM_MIN_INCORRECT_STREAK', 3),
        'HARD_ITEM_MAX_REPETITIONS': DEFAULT_APP_CONFIGS.get('HARD_ITEM_MAX_REPETITIONS', 10),
        'FSRS_DESIRED_RETENTION': DEFAULT_APP_CONFIGS.get('FSRS_DESIRED_RETENTION', FSRSDefaultConfig.FSRS_DESIRED_RETENTION),
        'FSRS_MAX_INTERVAL': DEFAULT_APP_CONFIGS.get('FSRS_MAX_INTERVAL', FSRSDefaultConfig.FSRS_MAX_INTERVAL),
        'FSRS_ENABLE_FUZZ': DEFAULT_APP_CONFIGS.get('FSRS_ENABLE_FUZZ', FSRSDefaultConfig.FSRS_ENABLE_FUZZ),
        'FSRS_GLOBAL_WEIGHTS': DEFAULT_APP_CONFIGS.get('FSRS_GLOBAL_WEIGHTS', FSRSDefaultConfig.FSRS_GLOBAL_WEIGHTS),
        'QUIZ_RATING_EASY_MS': 3000,
        'QUIZ_RATING_GOOD_MS': 10000,
        'FSRS_DAILY_LIMIT': 200,
        'FSRS_FUZZ_THRESHOLD': 3.0,
        'FSRS_OPTIMIZER_THRESHOLD': 500,
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
            current_app.logger.debug(f"Could not load SRS config from DB: {e}")

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
    def get_fsrs_params(cls) -> Dict[str, Any]:
        return {
            'desired_retention': cls.get('FSRS_DESIRED_RETENTION'),
            'max_interval': cls.get('FSRS_MAX_INTERVAL'),
            'enable_fuzz': cls.get('FSRS_ENABLE_FUZZ'),
            'w': cls.get('FSRS_GLOBAL_WEIGHTS'),
        }

    @staticmethod
    def get_parameters():
        """Legacy compatibility method."""
        return FSRSSettingsService.get_fsrs_params()

    @staticmethod
    def save_parameters(data, user_id=None):
        for key, value in data.items():
            AppSettings.set(key, value, category=FSRSSettingsService.CATEGORY, user_id=user_id)
        db.session.commit()
        FSRSSettingsService.invalidate_cache()

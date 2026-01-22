"""
Memory Power Configuration Service

Provides centralized configuration for SRS/Memory Power system.
Retrieves settings from AppSettings with fallback to defaults.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from functools import lru_cache
import json

from flask import current_app

from ..models import AppSettings, db


from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS

class MemoryPowerConfigService:
    """Service for managing Memory Power / SRS configuration."""

    # Category for all SRS settings in AppSettings
    CATEGORY = 'srs'

    # Default values - Pulled from centralized core/defaults.py
    DEFAULTS: Dict[str, Any] = {
        # === Hard Item Logic ===
        'HARD_ITEM_MIN_INCORRECT_STREAK': DEFAULT_APP_CONFIGS.get('HARD_ITEM_MIN_INCORRECT_STREAK', 3),
        'HARD_ITEM_MAX_REPETITIONS': DEFAULT_APP_CONFIGS.get('HARD_ITEM_MAX_REPETITIONS', 10),

        # === FSRS-5 Parameters ===
        'FSRS_DESIRED_RETENTION': DEFAULT_APP_CONFIGS.get('FSRS_DESIRED_RETENTION'),
        'FSRS_MAX_INTERVAL': DEFAULT_APP_CONFIGS.get('FSRS_MAX_INTERVAL', 365),
        'FSRS_ENABLE_FUZZ': DEFAULT_APP_CONFIGS.get('FSRS_ENABLE_FUZZ', False),
        'FSRS_GLOBAL_WEIGHTS': DEFAULT_APP_CONFIGS.get('FSRS_GLOBAL_WEIGHTS'),

        # === Implicit Rating Thresholds (Quiz/Typing) ===
        'QUIZ_RATING_EASY_MS': 3000,
        'QUIZ_RATING_GOOD_MS': 10000,

        # === Advanced Optimizations ===
        'FSRS_DAILY_LIMIT': 200,
        'FSRS_FUZZ_THRESHOLD': 3.0,
        'FSRS_OPTIMIZER_THRESHOLD': 500,
    }

    # Setting descriptions for UI - DETAILED Vietnamese explanations
    DESCRIPTIONS: Dict[str, str] = {
        # Hard Items
        'HARD_ITEM_MIN_INCORRECT_STREAK': '''Số lần trả lời SAI liên tiếp để coi là "Từ khó".
Mặc định: 3. Nếu sai 3 lần liền -> vào danh sách Hard.''',

        'HARD_ITEM_MAX_REPETITIONS': '''Số lần học tối thiểu để kiểm tra xem có bị "kẹt" không.
Mặc định: 10.''',

        # FSRS-5 Parameters
        'FSRS_DESIRED_RETENTION': '''Mục tiêu tỷ lệ ghi nhớ (Desired Retention) cho thuật toán FSRS-5.
Giá trị từ 0.7 đến 0.97. Mặc định: 0.9 (90%).
• Cao hơn (0.95): Ôn thường xuyên hơn, interval ngắn hơn
• Thấp hơn (0.85): Ôn ít hơn, interval dài hơn
Đây là thông số quan trọng nhất ảnh hưởng đến lịch ôn tập.''',

        'FSRS_MAX_INTERVAL': '''Giới hạn khoảng cách ôn tập tối đa (ngày).
Mặc định: 365 ngày.''',

        'FSRS_ENABLE_FUZZ': '''Bật/Tắt tính năng làm mờ lịch (Fuzzing).
Giúp phân tán tải ôn tập bằng cách thêm biến thiên ngẫu nhiên nhỏ.''',

        'FSRS_GLOBAL_WEIGHTS': '''Các tham số trọng số (w) của thuật toán FSRS.
Đây là các hệ số được tối ưu hóa từ lịch sử học của bạn.
⚠️ CHỈ thay đổi nếu bạn hiểu rõ thuật toán FSRS!
Format JSON: Mảng số thực (thường là 17 hoặc 19 số tùy phiên bản). Để khôi phục mặc định, nhấn "Reset".''',

        'QUIZ_RATING_EASY_MS': '''Thời gian trả lời tối đa (ms) để được coi là "Dễ" (Rating 4) trong chế độ Quiz.
Mặc định: 3000 (3 giây).''',
        'QUIZ_RATING_GOOD_MS': '''Thời gian trả lời tối đa (ms) để được coi là "Tốt" (Rating 3) trong chế độ Quiz.
Mặc định: 10000 (10 giây). Nếu vượt quá sẽ coi là "Khó" (Rating 2).''',

        'FSRS_DAILY_LIMIT': '''Giới hạn số thẻ ôn tập tối đa mỗi ngày để cân bằng tải.
Nếu vượt quá giới hạn này, card có độ ưu tiên thấp sẽ được dời sang ngày khác (+/- 1 ngày).
Mặc định: 200 thẻ.''',
        'FSRS_FUZZ_THRESHOLD': '''Ngưỡng interval (ngày) để bắt đầu áp dụng Fuzzing (làm mờ lịch).
Mặc định: 3.0 ngày. Các card có interval ngắn hơn sẽ không bị fuzz để đảm bảo độ chính xác.''',
        'FSRS_OPTIMIZER_THRESHOLD': '''Số lượng review log tối thiểu để tự động kích hoạt tối ưu hóa tham số (Optimization).
Mặc định: 500 review.''',
    }

    # Data types for form rendering
    DATA_TYPES: Dict[str, str] = {
        'HARD_ITEM_MIN_INCORRECT_STREAK': 'int',
        'HARD_ITEM_MAX_REPETITIONS': 'int',
        # FSRS-5
        'FSRS_DESIRED_RETENTION': 'float',
        'FSRS_MAX_INTERVAL': 'int',
        'FSRS_ENABLE_FUZZ': 'bool',
        'FSRS_GLOBAL_WEIGHTS': 'json',
        'QUIZ_RATING_EASY_MS': 'int',
        'QUIZ_RATING_GOOD_MS': 'int',
        'FSRS_DAILY_LIMIT': 'int',
        'FSRS_FUZZ_THRESHOLD': 'float',
        'FSRS_OPTIMIZER_THRESHOLD': 'int',
    }

    # Group settings for UI display
    GROUPS: Dict[str, Dict[str, Any]] = {
        'hard_items': {
            'label': 'Cấu hình Thẻ Khó',
            'icon': 'fas fa-exclamation-triangle',
            'keys': [
                'HARD_ITEM_MIN_INCORRECT_STREAK',
                'HARD_ITEM_MAX_REPETITIONS',
            ],
        },
        'fsrs': {
            'label': 'FSRS-5 (Thuật toán lập lịch)',
            'icon': 'fas fa-cogs',
            'keys': [
                'FSRS_DESIRED_RETENTION',
                'FSRS_MAX_INTERVAL',
                'FSRS_ENABLE_FUZZ',
                'FSRS_GLOBAL_WEIGHTS',
                'QUIZ_RATING_EASY_MS',
                'QUIZ_RATING_GOOD_MS',
                'FSRS_DAILY_LIMIT',
                'FSRS_FUZZ_THRESHOLD',
                'FSRS_OPTIMIZER_THRESHOLD',
            ],
        },
    }

    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False

    @classmethod
    def _ensure_cache(cls) -> None:
        """Load all SRS settings into cache if not already loaded."""
        if cls._cache_loaded:
            return

        try:
            settings = AppSettings.get_by_category(cls.CATEGORY)
            for setting in settings:
                cls._cache[setting.key] = setting.value
            cls._cache_loaded = True
        except Exception as e:
            # During app initialization, DB may not be available
            current_app.logger.debug(f"Could not load SRS config from DB: {e}")

    @classmethod
    def invalidate_cache(cls) -> None:
        """Clear the config cache (call after saving new settings)."""
        cls._cache.clear()
        cls._cache_loaded = False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Setting key (e.g., 'HARD_ITEM_MIN_INCORRECT_STREAK')
            default: Fallback if neither DB nor DEFAULTS have the key

        Returns:
            The configuration value
        """
        cls._ensure_cache()

        # Check cache first (from DB)
        if key in cls._cache:
            return cls._cache[key]

        # Fallback to defaults
        if key in cls.DEFAULTS:
            return cls.DEFAULTS[key]

        return default

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all SRS settings with current values."""
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
        """
        Save a configuration value to DB.

        Args:
            key: Setting key
            value: Value to save
            user_id: ID of admin making the change
        """
        if key not in cls.DEFAULTS:
            raise ValueError(f"Unknown SRS setting key: {key}")

        AppSettings.set(
            key=key,
            value=value,
            category=cls.CATEGORY,
            data_type=cls.DATA_TYPES.get(key, 'string'),
            description=cls.DESCRIPTIONS.get(key, ''),
            user_id=user_id,
        )

        # Update cache
        cls._cache[key] = value

    @classmethod
    def save_all(cls, settings: Dict[str, Any], user_id: int = None) -> None:
        """
        Save multiple settings at once.

        Args:
            settings: Dict of key -> value
            user_id: ID of admin making the change
        """
        for key, value in settings.items():
            if key in cls.DEFAULTS:
                cls.set(key, value, user_id)

        db.session.commit()
        cls.invalidate_cache()

    @classmethod
    def reset_to_defaults(cls, user_id: int = None) -> None:
        """Reset all SRS settings to default values."""
        for key, value in cls.DEFAULTS.items():
            cls.set(key, value, user_id)

        db.session.commit()
        cls.invalidate_cache()

    # === Convenience Getters for MemoryEngine ===

    @classmethod
    def get_fsrs_params(cls) -> Dict[str, Any]:
        """Utility to get all FSRS v5 core params in one dict."""
        return {
            'desired_retention': cls.get('FSRS_DESIRED_RETENTION'),
            'max_interval': cls.get('FSRS_MAX_INTERVAL'),
            'enable_fuzz': cls.get('FSRS_ENABLE_FUZZ'),
            'w': cls.get('FSRS_GLOBAL_WEIGHTS'),
        }

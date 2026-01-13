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


class MemoryPowerConfigService:
    """Service for managing Memory Power / SRS configuration."""

    # Category for all SRS settings in AppSettings
    CATEGORY = 'srs'

    # Default values - used when no DB config exists
    DEFAULTS: Dict[str, Any] = {
        # === Interval Constants (in minutes) ===
        'SRS_LEARNING_INTERVALS': [1, 10, 60, 240, 480, 1440],  # 1m, 10m, 1h, 4h, 8h, 1d
        'SRS_GRADUATING_INTERVAL': 5760,  # 4 days in minutes
        'SRS_RELEARNING_INTERVAL': 10,
        'SRS_MIN_INTERVAL': 1,
        'SRS_RETENTION_THRESHOLD': 0.90,
        'SRS_LEARNING_TO_REVIEWING_STREAK': 7,

        # === Flashcard Quality Mappings ===
        # 3-button mode: Forgot -> 1, Hard -> 3, Easy -> 5
        'SRS_FLASHCARD_3BTN_MAPPING': {'1': 1, '2': 3, '3': 5},
        # 4-button mode: Forgot -> 0, Hard -> 2, Good -> 4, Easy -> 5
        'SRS_FLASHCARD_4BTN_MAPPING': {'1': 0, '2': 2, '3': 4, '4': 5},

        # === Quiz Quality Settings ===
        'SRS_QUIZ_CORRECT_QUALITY': 4,
        'SRS_QUIZ_INCORRECT_QUALITY': 1,

        # === Typing Quality Thresholds ===
        # Accuracy thresholds: [perfect, minor_typo, mostly_correct, half_correct]
        # >=1.0 -> 5, >=0.9 -> 4, >=0.7 -> 3, >=0.5 -> 2, else -> 1
        'SRS_TYPING_THRESHOLDS': {
            'perfect': 1.0,       # -> quality 5
            'minor_typo': 0.9,    # -> quality 4
            'mostly_correct': 0.7, # -> quality 3
            'half_correct': 0.5,  # -> quality 2
            # Below 0.5 -> quality 1
        },
        'SRS_TYPING_HINT_QUALITY': 2,

        # === Mastery Calculation Parameters ===
        # Learning phase
        'SRS_LEARNING_BASE_MASTERY': 0.10,
        'SRS_LEARNING_MASTERY_PER_REP': 0.06,
        'SRS_LEARNING_MAX_MASTERY': 0.52,
        'SRS_LEARNING_STREAK_BONUS_START': 3,  # Bonus starts after this streak
        'SRS_LEARNING_STREAK_BONUS_PER': 0.01,

        # Reviewing phase
        'SRS_REVIEWING_BASE_MASTERY': 0.60,
        'SRS_REVIEWING_MASTERY_PER_REP': 0.057,
        'SRS_REVIEWING_MAX_MASTERY': 1.0,
        'SRS_REVIEWING_STREAK_BONUS_START': 5,
        'SRS_REVIEWING_STREAK_BONUS_PER': 0.02,

        # Incorrect penalty
        'SRS_INCORRECT_PENALTY_HIGH_MASTERY': 0.15,  # Penalty when mastery > 0.7
        'SRS_INCORRECT_PENALTY_LOW_MASTERY': 0.20,   # Penalty when mastery <= 0.7
        'SRS_INCORRECT_MIN_MASTERY': 0.10,

        # === Hard Item Logic ===
        'HARD_ITEM_MIN_INCORRECT_STREAK': 3,
        'HARD_ITEM_MAX_REPETITIONS': 10,
        'HARD_ITEM_LOW_MASTERY_THRESHOLD': 0.3,
    }

    # Setting descriptions for UI - DETAILED Vietnamese explanations
    DESCRIPTIONS: Dict[str, str] = {
        # Intervals
        'SRS_LEARNING_INTERVALS': '''Danh sách khoảng thời gian (phút) cho giai đoạn Learning.
Sau mỗi lần trả lời đúng, thẻ sẽ được lên lịch theo thứ tự: 1→10→60→240→480→1440 phút.
VD: Mặc định [1, 10, 60, 240, 480, 1440] = 1 phút → 10 phút → 1 giờ → 4 giờ → 8 giờ → 1 ngày.''',

        'SRS_GRADUATING_INTERVAL': '''Khoảng thời gian (phút) khi thẻ "tốt nghiệp" từ Learning sang Reviewing.
Mặc định: 5760 phút = 4 ngày. Đây là interval đầu tiên khi thẻ vào giai đoạn Reviewing.''',

        'SRS_RELEARNING_INTERVAL': '''Thời gian chờ (phút) khi trả lời SAI.
Thẻ sẽ xuất hiện lại sau khoảng thời gian này. Mặc định: 10 phút.''',

        'SRS_MIN_INTERVAL': '''Khoảng thời gian tối thiểu (phút) giữa các lần ôn.
Mặc định: 1 phút. Không có interval nào dưới mức này.''',

        'SRS_RETENTION_THRESHOLD': '''Ngưỡng Retention để đánh dấu thẻ cần ôn lại (0.0 - 1.0).
Khi Retention xuống dưới ngưỡng này, thẻ được coi là "due".
Mặc định: 0.90 = 90%. Công thức: Retention = e^(-t/S) với t = thời gian, S = stability.''',

        'SRS_LEARNING_TO_REVIEWING_STREAK': '''Số câu trả lời ĐÚNG liên tiếp để chuyển từ Learning sang Reviewing.
Mặc định: 7 lần đúng liên tiếp mới được "tốt nghiệp" giai đoạn Learning.''',

        # Flashcard mappings
        'SRS_FLASHCARD_3BTN_MAPPING': '''Ánh xạ 3 nút Flashcard sang Quality Score (0-5):
• Nút 1 (Quên): Quality = 1 (sai, cần ôn lại ngay)
• Nút 2 (Khó): Quality = 3 (đúng nhưng khó khăn)
• Nút 3 (Dễ): Quality = 5 (nhớ hoàn hảo)
Format JSON: {"1": 1, "2": 3, "3": 5}''',

        'SRS_FLASHCARD_4BTN_MAPPING': '''Ánh xạ 4 nút Flashcard sang Quality Score (0-5):
• Nút 1 (Quên hoàn toàn): Quality = 0
• Nút 2 (Khó/Mơ hồ): Quality = 2
• Nút 3 (Nhớ được): Quality = 4
• Nút 4 (Dễ dàng): Quality = 5
Format JSON: {"1": 0, "2": 2, "3": 4, "4": 5}''',

        # Quiz
        'SRS_QUIZ_CORRECT_QUALITY': '''Quality Score khi trả lời Quiz ĐÚNG (0-5).
Mặc định: 4 (Nhớ tốt với chút cố gắng). 
Giá trị cao hơn = interval tăng nhanh hơn.''',

        'SRS_QUIZ_INCORRECT_QUALITY': '''Quality Score khi trả lời Quiz SAI (0-5).
Mặc định: 1 (Sai, cần ôn lại).
Quality < 3 = câu trả lời sai, interval reset.''',

        # Typing
        'SRS_TYPING_THRESHOLDS': '''Ngưỡng accuracy (0.0-1.0) cho Typing mode:
• perfect (>=1.0): Quality 5 - Gõ đúng 100%
• minor_typo (>=0.9): Quality 4 - Lỗi nhỏ <10%
• mostly_correct (>=0.7): Quality 3 - Đúng 70-90%
• half_correct (>=0.5): Quality 2 - Đúng 50-70%
• Dưới 0.5: Quality 1 - Sai quá nhiều''',

        'SRS_TYPING_HINT_QUALITY': '''Quality Score khi dùng HINT trong Typing (0-5).
Mặc định: 2 (Đúng nhưng cần trợ giúp).
Dùng hint = không được tính là nhớ tốt.''',

        # Learning Mastery
        'SRS_LEARNING_BASE_MASTERY': '''Mastery cơ bản khi BẮT ĐẦU giai đoạn Learning.
Mặc định: 0.10 = 10%. Đây là Mastery tối thiểu khi thẻ mới vào Learning.''',

        'SRS_LEARNING_MASTERY_PER_REP': '''Mastery TĂNG THÊM cho mỗi lần ôn đúng trong Learning.
Mặc định: 0.06 = +6% mỗi lần.
VD: Sau 5 lần đúng = 10% + 5×6% = 40% Mastery.''',

        'SRS_LEARNING_MAX_MASTERY': '''Mastery TỐI ĐA trong giai đoạn Learning.
Mặc định: 0.52 = 52%. Không thể vượt quá mức này khi còn trong Learning.''',

        'SRS_LEARNING_STREAK_BONUS_START': '''Bắt đầu cộng bonus streak SAU bao nhiêu câu đúng liên tiếp.
Mặc định: 3. VD: Streak 5 = bonus từ câu thứ 4, 5.''',

        'SRS_LEARNING_STREAK_BONUS_PER': '''Bonus Mastery cho MỖI câu đúng vượt ngưỡng streak.
Mặc định: 0.01 = +1% mỗi câu đúng liên tiếp sau ngưỡng.''',

        # Reviewing Mastery
        'SRS_REVIEWING_BASE_MASTERY': '''Mastery cơ bản khi BẮT ĐẦU giai đoạn Reviewing.
Mặc định: 0.60 = 60%. Đây là Mastery khi thẻ vừa "tốt nghiệp" Learning.''',

        'SRS_REVIEWING_MASTERY_PER_REP': '''Mastery TĂNG THÊM cho mỗi lần ôn đúng trong Reviewing.
Mặc định: 0.057 = +5.7% mỗi lần.
VD: Sau 7 lần đúng trong Reviewing = 60% + 7×5.7% ≈ 100%.''',

        'SRS_REVIEWING_MAX_MASTERY': '''Mastery TỐI ĐA trong giai đoạn Reviewing.
Mặc định: 1.0 = 100%. Đây là mức hoàn hảo!''',

        'SRS_REVIEWING_STREAK_BONUS_START': '''Bắt đầu bonus streak trong Reviewing sau bao nhiêu câu đúng.
Mặc định: 5. Reviewing cần nhiều câu đúng hơn để có bonus.''',

        'SRS_REVIEWING_STREAK_BONUS_PER': '''Bonus Mastery cho mỗi câu đúng vượt ngưỡng trong Reviewing.
Mặc định: 0.02 = +2% (cao hơn Learning vì đây là giai đoạn ổn định).''',

        # Penalty
        'SRS_INCORRECT_PENALTY_HIGH_MASTERY': '''Mức phạt Mastery cho mỗi câu SAI khi Mastery > 70%.
Mặc định: 0.15 = -15% mỗi lần sai. Thẻ đã thuộc tốt → phạt nhẹ hơn.''',

        'SRS_INCORRECT_PENALTY_LOW_MASTERY': '''Mức phạt Mastery cho mỗi câu SAI khi Mastery ≤ 70%.
Mặc định: 0.20 = -20% mỗi lần sai. Thẻ chưa thuộc → phạt nặng hơn.''',

        'SRS_INCORRECT_MIN_MASTERY': '''Mastery TỐI THIỂU sau khi bị phạt.
Mặc định: 0.10 = 10%. Mastery không bao giờ xuống dưới mức này.''',

        # Hard Logic
        'HARD_ITEM_MIN_INCORRECT_STREAK': '''Số lần trả lời SAI liên tiếp để coi là "Từ khó".
Mặc định: 3. Nếu sai 3 lần liền -> vào danh sách Hard.''',

        'HARD_ITEM_MAX_REPETITIONS': '''Số lần học tối thiểu để kiểm tra xem có bị "kẹt" không.
Mặc định: 10. Nếu đã học > 10 lần mà Mastery vẫn thấp -> coi là khó.''',

        'HARD_ITEM_LOW_MASTERY_THRESHOLD': '''Ngưỡng Mastery thấp để xác định thẻ "học mãi không vào".
Mặc định: 0.3 (30%). Nếu Reps > 10 và Mastery < 30% -> vào danh sách Hard.''',
    }

    # Data types for form rendering
    DATA_TYPES: Dict[str, str] = {
        'SRS_LEARNING_INTERVALS': 'json',
        'SRS_GRADUATING_INTERVAL': 'int',
        'SRS_RELEARNING_INTERVAL': 'int',
        'SRS_MIN_INTERVAL': 'int',
        'SRS_RETENTION_THRESHOLD': 'float',
        'SRS_LEARNING_TO_REVIEWING_STREAK': 'int',
        'SRS_FLASHCARD_3BTN_MAPPING': 'json',
        'SRS_FLASHCARD_4BTN_MAPPING': 'json',
        'SRS_QUIZ_CORRECT_QUALITY': 'int',
        'SRS_QUIZ_INCORRECT_QUALITY': 'int',
        'SRS_TYPING_THRESHOLDS': 'json',
        'SRS_TYPING_HINT_QUALITY': 'int',
        'SRS_LEARNING_BASE_MASTERY': 'float',
        'SRS_LEARNING_MASTERY_PER_REP': 'float',
        'SRS_LEARNING_MAX_MASTERY': 'float',
        'SRS_LEARNING_STREAK_BONUS_START': 'int',
        'SRS_LEARNING_STREAK_BONUS_PER': 'float',
        'SRS_REVIEWING_BASE_MASTERY': 'float',
        'SRS_REVIEWING_MASTERY_PER_REP': 'float',
        'SRS_REVIEWING_MAX_MASTERY': 'float',
        'SRS_REVIEWING_STREAK_BONUS_START': 'int',
        'SRS_REVIEWING_STREAK_BONUS_PER': 'float',
        'SRS_INCORRECT_PENALTY_HIGH_MASTERY': 'float',
        'SRS_INCORRECT_PENALTY_LOW_MASTERY': 'float',
        'SRS_INCORRECT_MIN_MASTERY': 'float',
        'HARD_ITEM_MIN_INCORRECT_STREAK': 'int',
        'HARD_ITEM_MAX_REPETITIONS': 'int',
        'HARD_ITEM_LOW_MASTERY_THRESHOLD': 'float',
    }

    # Group settings for UI display
    GROUPS: Dict[str, Dict[str, Any]] = {
        'intervals': {
            'label': 'Khoảng thời gian ôn tập',
            'icon': 'fas fa-clock',
            'keys': [
                'SRS_LEARNING_INTERVALS',
                'SRS_GRADUATING_INTERVAL',
                'SRS_RELEARNING_INTERVAL',
                'SRS_MIN_INTERVAL',
                'SRS_RETENTION_THRESHOLD',
                'SRS_LEARNING_TO_REVIEWING_STREAK',
            ],
        },
        'flashcard': {
            'label': 'Cấu hình Flashcard',
            'icon': 'fas fa-layer-group',
            'keys': [
                'SRS_FLASHCARD_3BTN_MAPPING',
                'SRS_FLASHCARD_4BTN_MAPPING',
            ],
        },
        'quiz': {
            'label': 'Cấu hình Quiz',
            'icon': 'fas fa-question-circle',
            'keys': [
                'SRS_QUIZ_CORRECT_QUALITY',
                'SRS_QUIZ_INCORRECT_QUALITY',
            ],
        },
        'typing': {
            'label': 'Cấu hình Typing',
            'icon': 'fas fa-keyboard',
            'keys': [
                'SRS_TYPING_THRESHOLDS',
                'SRS_TYPING_HINT_QUALITY',
            ],
        },
        'mastery': {
            'label': 'Tính toán Mastery',
            'icon': 'fas fa-brain',
            'keys': [
                'SRS_LEARNING_BASE_MASTERY',
                'SRS_LEARNING_MASTERY_PER_REP',
                'SRS_LEARNING_MAX_MASTERY',
                'SRS_LEARNING_STREAK_BONUS_START',
                'SRS_LEARNING_STREAK_BONUS_PER',
                'SRS_REVIEWING_BASE_MASTERY',
                'SRS_REVIEWING_MASTERY_PER_REP',
                'SRS_REVIEWING_MAX_MASTERY',
                'SRS_REVIEWING_STREAK_BONUS_START',
                'SRS_REVIEWING_STREAK_BONUS_PER',
                'SRS_INCORRECT_PENALTY_HIGH_MASTERY',
                'SRS_INCORRECT_PENALTY_LOW_MASTERY',
                'SRS_INCORRECT_MIN_MASTERY',
            ],
        },
        'hard_items': {
            'label': 'Cấu hình Thẻ Khó',
            'icon': 'fas fa-exclamation-triangle',
            'keys': [
                'HARD_ITEM_MIN_INCORRECT_STREAK',
                'HARD_ITEM_MAX_REPETITIONS',
                'HARD_ITEM_LOW_MASTERY_THRESHOLD',
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
            key: Setting key (e.g., 'SRS_LEARNING_INTERVALS')
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
    def get_learning_intervals(cls) -> List[int]:
        """Get learning phase intervals in minutes."""
        return cls.get('SRS_LEARNING_INTERVALS')

    @classmethod
    def get_graduating_interval(cls) -> int:
        """Get interval when graduating from Learning to Reviewing."""
        return cls.get('SRS_GRADUATING_INTERVAL')

    @classmethod
    def get_relearning_interval(cls) -> int:
        """Get interval after incorrect answer."""
        return cls.get('SRS_RELEARNING_INTERVAL')

    @classmethod
    def get_min_interval(cls) -> int:
        """Get minimum interval."""
        return cls.get('SRS_MIN_INTERVAL')

    @classmethod
    def get_flashcard_quality_mapping(cls, button_count: int) -> Dict[int, int]:
        """
        Get flashcard button-to-quality mapping.

        Args:
            button_count: 3 or 4

        Returns:
            Dict mapping button number to quality score
        """
        if button_count == 3:
            mapping = cls.get('SRS_FLASHCARD_3BTN_MAPPING')
        elif button_count == 4:
            mapping = cls.get('SRS_FLASHCARD_4BTN_MAPPING')
        else:
            return {}

        # Convert string keys to int if needed
        return {int(k): v for k, v in mapping.items()}

    @classmethod
    def get_quiz_quality(cls, is_correct: bool) -> int:
        """Get quality score for quiz answer."""
        if is_correct:
            return cls.get('SRS_QUIZ_CORRECT_QUALITY')
        return cls.get('SRS_QUIZ_INCORRECT_QUALITY')

    @classmethod
    def get_typing_quality(cls, accuracy: float, used_hint: bool = False) -> int:
        """
        Get quality score for typing accuracy.

        Args:
            accuracy: 0.0 - 1.0
            used_hint: Whether hint was used

        Returns:
            Quality score 1-5
        """
        if used_hint:
            return cls.get('SRS_TYPING_HINT_QUALITY')

        thresholds = cls.get('SRS_TYPING_THRESHOLDS')

        if accuracy >= thresholds.get('perfect', 1.0):
            return 5
        elif accuracy >= thresholds.get('minor_typo', 0.9):
            return 4
        elif accuracy >= thresholds.get('mostly_correct', 0.7):
            return 3
        elif accuracy >= thresholds.get('half_correct', 0.5):
            return 2
        else:
            return 1

    @classmethod
    def get_mastery_params(cls, status: str) -> Dict[str, float]:
        """
        Get mastery calculation parameters for a status.

        Args:
            status: 'learning' or 'reviewing'

        Returns:
            Dict with base, per_rep, max, streak_start, streak_per
        """
        if status == 'learning':
            return {
                'base': cls.get('SRS_LEARNING_BASE_MASTERY'),
                'per_rep': cls.get('SRS_LEARNING_MASTERY_PER_REP'),
                'max': cls.get('SRS_LEARNING_MAX_MASTERY'),
                'streak_start': cls.get('SRS_LEARNING_STREAK_BONUS_START'),
                'streak_per': cls.get('SRS_LEARNING_STREAK_BONUS_PER'),
            }
        elif status == 'reviewing':
            return {
                'base': cls.get('SRS_REVIEWING_BASE_MASTERY'),
                'per_rep': cls.get('SRS_REVIEWING_MASTERY_PER_REP'),
                'max': cls.get('SRS_REVIEWING_MAX_MASTERY'),
                'streak_start': cls.get('SRS_REVIEWING_STREAK_BONUS_START'),
                'streak_per': cls.get('SRS_REVIEWING_STREAK_BONUS_PER'),
            }
        return {}

    @classmethod
    def get_incorrect_penalty_params(cls) -> Dict[str, float]:
        """Get parameters for incorrect answer penalty calculation."""
        return {
            'high_mastery_penalty': cls.get('SRS_INCORRECT_PENALTY_HIGH_MASTERY'),
            'low_mastery_penalty': cls.get('SRS_INCORRECT_PENALTY_LOW_MASTERY'),
            'min_mastery': cls.get('SRS_INCORRECT_MIN_MASTERY'),
        }

"""Dịch vụ nạp cấu hình động từ cơ sở dữ liệu."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from flask import Flask, current_app, has_app_context

from ..models import AppSettings, db
from ..logics.config_parser import ConfigParser

# Các khóa nhạy cảm không được ghi đè từ DB
SENSITIVE_SETTING_KEYS = {"SECRET_KEY", "SQLALCHEMY_DATABASE_URI"}


class ConfigService:
    """Đồng bộ cấu hình giữa DB và current_app.config."""

    def __init__(self, app, ttl_seconds: int = 30) -> None:
        self.app = app
        self.ttl_seconds = ttl_seconds
        self._last_loaded: datetime | None = None

    def ensure_defaults(self, defaults: Iterable[dict[str, object]]) -> None:
        """Đảm bảo các cấu hình mặc định tồn tại trong cơ sở dữ liệu."""

        created = False
        for payload in defaults:
            key = str(payload.get("key", "")).strip()
            if not key:
                continue

            if AppSettings.query.get(key):
                continue

            setting = AppSettings(
                key=key,
                value=payload.get("value"),
                category=payload.get("category", "system"),
                data_type=str(payload.get("data_type") or "string"),
                description=payload.get("description"),
            )
            db.session.add(setting)
            created = True

        if created:
            db.session.commit()

    def _parse_value(self, setting: AppSettings) -> Any:
        """Parse setting value using ConfigParser logic."""
        # Use explicit data_type if available, else infer from key
        data_type = getattr(setting, "data_type", None)
        if not data_type:
            data_type = ConfigParser.infer_data_type(setting.key)
        else:
            data_type = str(data_type).lower()
        
        try:
            return ConfigParser.parse_value(setting.value, data_type)
        except (TypeError, ValueError) as e:
            current_app.logger.warning(
                "Không thể chuyển đổi giá trị của %s ('%s') về kiểu %s: %s. Dùng giá trị mặc định.",
                setting.key,
                setting.value,
                data_type,
                e,
            )
            # Return safe defaults
            if data_type == 'int':
                return 0
            if data_type == 'bool':
                return False
            return setting.value

    def load_settings(self, force: bool = False) -> None:
        """Nạp toàn bộ AppSettings vào current_app.config."""

        if not has_app_context():
            raise RuntimeError("ConfigService yêu cầu app context để nạp cấu hình.")

        now = datetime.now(timezone.utc)
        if not force and self._last_loaded and (now - self._last_loaded) < timedelta(seconds=self.ttl_seconds):
            return

        # Load all non-template settings (template settings are loaded separately by TemplateService)
        settings = AppSettings.query.filter(AppSettings.category != 'template').all()
        for setting in settings:
            if setting.key.upper() in SENSITIVE_SETTING_KEYS:
                current_app.logger.info("Bỏ qua cấu hình nhạy cảm %s từ DB", setting.key)
                continue

            self.app.config[setting.key] = self._parse_value(setting)

        self._last_loaded = now


def get_runtime_config(key: str, default: Any = None) -> Any:
    """Lấy cấu hình ưu tiên từ current_app, fallback về mặc định."""

    if has_app_context():
        return current_app.config.get(key, default)
    return default


def init_config_service(app, ttl_seconds: int = 30) -> ConfigService:
    """Khởi tạo dịch vụ cấu hình và đăng ký middleware làm mới."""

    service = ConfigService(app, ttl_seconds=ttl_seconds)
    app.extensions["config_service"] = service

    def _default_settings(app_obj: Flask) -> list[dict[str, object]]:
        from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
        return [
            {
                "key": "AI_PROVIDER",
                "value": DEFAULT_APP_CONFIGS.get("AI_PROVIDER"),
                "data_type": "string",
                "description": "Dịch vụ AI được sử dụng chính (gemini hoặc huggingface).",
            },
            {
                "key": "GEMINI_MODEL",
                "value": DEFAULT_APP_CONFIGS.get("GEMINI_MODEL"),
                "data_type": "string",
                "description": "Model mặc định khi sử dụng Google Gemini.",
            },
            {
                "key": "HUGGINGFACE_MODEL",
                "value": DEFAULT_APP_CONFIGS.get("HUGGINGFACE_MODEL"),
                "data_type": "string",
                "description": "Model mặc định khi sử dụng Hugging Face.",
            },
            {
                "key": "SCORE_FSRS_AGAIN",
                "value": DEFAULT_APP_CONFIGS.get("SCORE_FSRS_AGAIN"),
                "data_type": "int",
                "description": "Điểm khi chọn Again (Quên).",
            },
            {
                "key": "SCORE_FSRS_HARD",
                "value": DEFAULT_APP_CONFIGS.get("SCORE_FSRS_HARD"),
                "data_type": "int",
                "description": "Điểm khi chọn Hard (Khó).",
            },
            {
                "key": "SCORE_FSRS_GOOD",
                "value": DEFAULT_APP_CONFIGS.get("SCORE_FSRS_GOOD"),
                "data_type": "int",
                "description": "Điểm khi chọn Good (Được).",
            },
            {
                "key": "SCORE_FSRS_EASY",
                "value": DEFAULT_APP_CONFIGS.get("SCORE_FSRS_EASY"),
                "data_type": "int",
                "description": "Điểm khi chọn Easy (Dễ).",
            },
            {
                "key": "QUIZ_FIRST_TIME_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("QUIZ_FIRST_TIME_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng cho lần đầu làm câu hỏi trắc nghiệm.",
            },
            {
                "key": "QUIZ_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("QUIZ_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi trả lời đúng câu hỏi trắc nghiệm.",
            },
            {
                "key": "COURSE_LESSON_COMPLETION_SCORE",
                "value": DEFAULT_APP_CONFIGS.get("COURSE_LESSON_COMPLETION_SCORE"),
                "data_type": "int",
                "description": "Điểm thưởng hoàn thành 1 bài học trong khóa.",
            },
            {
                "key": "COURSE_COMPLETION_SCORE",
                "value": DEFAULT_APP_CONFIGS.get("COURSE_COMPLETION_SCORE"),
                "data_type": "int",
                "description": "Điểm thưởng hoàn thành toàn bộ khóa học.",
            },
            {
                "key": "VOCAB_TYPING_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("VOCAB_TYPING_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi trả lời đúng (Typing).",
            },
            {
                "key": "VOCAB_MATCHING_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("VOCAB_MATCHING_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi ghép đúng cặp (Matching).",
            },
            {
                "key": "VOCAB_LISTENING_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("VOCAB_LISTENING_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi nghe và chọn đúng (Listening).",
            },
             {
                "key": "VOCAB_SPEED_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("VOCAB_SPEED_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi trả lời đúng trong Speed Review.",
            },
            {
                "key": "VOCAB_MCQ_CORRECT_BONUS",
                "value": DEFAULT_APP_CONFIGS.get("VOCAB_MCQ_CORRECT_BONUS"),
                "data_type": "int",
                "description": "Điểm thưởng khi trả lời đúng trắc nghiệm (Vocabulary MCQ).",
            },
            {
                "key": "DAILY_LOGIN_SCORE",
                "value": DEFAULT_APP_CONFIGS.get("DAILY_LOGIN_SCORE"),
                "data_type": "int",
                "description": "Điểm thưởng cho lần đăng nhập đầu tiên trong ngày.",
            },
            {
                "key": "MAINTENANCE_MODE",
                "value": DEFAULT_APP_CONFIGS.get("MAINTENANCE_MODE"),
                "data_type": "bool",
                "description": "Bật/Tắt chế độ bảo trì hệ thống.",
            },
            {
                "key": "MAINTENANCE_END_TIME",
                "value": DEFAULT_APP_CONFIGS.get("MAINTENANCE_END_TIME"),
                "data_type": "string",
                "description": "Thời điểm kết thúc bảo trì (ISO 8601, ví dụ: 2026-12-31T23:59:59).",
            },
            # --- Audio Defaults ---
            {
                "key": "AUDIO_DEFAULT_ENGINE",
                "value": DEFAULT_APP_CONFIGS.get("AUDIO_DEFAULT_ENGINE"),
                "data_type": "string",
                "category": "audio",
                "description": "Engine Text-to-Speech mặc định (edge hoặc gtts).",
            },
            {
                "key": "AUDIO_DEFAULT_VOICE_EDGE",
                "value": DEFAULT_APP_CONFIGS.get("AUDIO_DEFAULT_VOICE_EDGE"),
                "data_type": "string",
                "category": "audio",
                "description": "Giọng đọc mặc định cho Edge TTS.",
            },
            {
                "key": "AUDIO_DEFAULT_VOICE_GTTS",
                "value": DEFAULT_APP_CONFIGS.get("AUDIO_DEFAULT_VOICE_GTTS"),
                "data_type": "string",
                "category": "audio",
                "description": "Giọng đọc mặc định cho Google TTS.",
            },
        ]

    @app.before_request
    def refresh_config_from_db() -> None:  # pragma: no cover - hook
        service.load_settings()

    with app.app_context():
        service.ensure_defaults(_default_settings(app))
        service.load_settings(force=True)

    return service

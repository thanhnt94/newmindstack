"""Dịch vụ nạp cấu hình động từ cơ sở dữ liệu."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from flask import Flask, current_app, has_app_context

from ..models import SystemSetting, db

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

            if SystemSetting.query.filter_by(key=key).first():
                continue

            setting = SystemSetting(
                key=key,
                value=payload.get("value"),
                data_type=str(payload.get("data_type") or "string"),
                description=payload.get("description"),
            )
            db.session.add(setting)
            created = True

        if created:
            db.session.commit()

    def _infer_data_type(self, setting: SystemSetting) -> str:
        if getattr(setting, "data_type", None):
            return str(setting.data_type).lower()

        key = setting.key.upper()
        if key.startswith(("IS_", "HAS_", "ENABLE_")) or key.endswith(("_ENABLED", "_ENABLE")):
            return "bool"
        if key.endswith(("_COUNT", "_LIMIT", "_TIMEOUT", "_TTL", "_SECONDS", "_MINUTES")):
            return "int"
        if key.endswith(("_FOLDER", "_PATH", "_DIR", "_DIRECTORY")):
            return "path"
        return "string"

    def _parse_value(self, setting: SystemSetting) -> Any:
        raw_value = setting.value
        data_type = self._infer_data_type(setting)

        try:
            if data_type == "bool":
                if isinstance(raw_value, bool):
                    return raw_value
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(raw_value)

            if data_type == "int":
                if raw_value == '' or raw_value is None:
                    return 0
                return int(raw_value)

            if data_type == "path" and isinstance(raw_value, str):
                return os.path.abspath(raw_value)
        except (TypeError, ValueError):
            current_app.logger.warning(
                "Không thể chuyển đổi giá trị của %s ('%s') về kiểu %s, dùng giá trị mặc định an toàn.",
                setting.key,
                raw_value,
                data_type,
            )
            if data_type == 'int':
                return 0
            if data_type == 'bool':
                return False

        return raw_value

    def load_settings(self, force: bool = False) -> None:
        """Nạp toàn bộ SystemSetting vào current_app.config."""

        if not has_app_context():
            raise RuntimeError("ConfigService yêu cầu app context để nạp cấu hình.")

        now = datetime.now(timezone.utc)
        if not force and self._last_loaded and (now - self._last_loaded) < timedelta(seconds=self.ttl_seconds):
            return

        settings = SystemSetting.query.all()
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
        return [
            {
                "key": "UPLOAD_FOLDER",
                "value": app_obj.config.get("UPLOAD_FOLDER"),
                "data_type": "path",
                "description": "Thư mục lưu trữ file tải lên (uploads).",
            },
            {
                "key": "BACKUP_FOLDER",
                "value": app_obj.config.get("BACKUP_FOLDER"),
                "data_type": "path",
                "description": "Thư mục lưu trữ bản sao lưu (backups).",
            },
            {
                "key": "DATABASE_URI",
                "value": app_obj.config.get("SQLALCHEMY_DATABASE_URI"),
                "data_type": "string",
                "description": "Chuỗi kết nối cơ sở dữ liệu ứng dụng.",
            },
            {
                "key": "AI_PROVIDER",
                "value": "gemini",
                "data_type": "string",
                "description": "Dịch vụ AI được sử dụng chính (gemini hoặc huggingface).",
            },
            {
                "key": "GEMINI_MODEL",
                "value": "gemini-2.0-flash-lite-001",
                "data_type": "string",
                "description": "Model mặc định khi sử dụng Google Gemini.",
            },
            {
                "key": "HUGGINGFACE_MODEL",
                "value": "google/gemma-7b-it",
                "data_type": "string",
                "description": "Model mặc định khi sử dụng Hugging Face.",
            },
            {
                "key": "DEFAULT_AUDIO_FOLDER",
                "value": "upload/audio",
                "data_type": "string",
                "description": "Thư mục mặc định lưu audio nếu container không có cấu hình riêng.",
            },
            {
                "key": "FLASHCARD_PREVIEW_BONUS",
                "value": 10,
                "data_type": "int",
                "description": "Điểm thưởng khi xem thẻ mới lần đầu.",
            },

            {
                "key": "FLASHCARD_EARLY_REVIEW_HIGH",
                "value": 10,
                "data_type": "int",
                "description": "Điểm khi ôn sớm và trả lời tốt (>=4).",
            },
            {
                "key": "FLASHCARD_EARLY_REVIEW_MEDIUM",
                "value": 5,
                "data_type": "int",
                "description": "Điểm khi ôn sớm và trả lời trung bình (>=2).",
            },
            {
                "key": "FLASHCARD_REVIEW_HIGH",
                "value": 10,
                "data_type": "int",
                "description": "Điểm khi ôn thẻ đúng hạn và trả lời tốt (>=4).",
            },
            {
                "key": "FLASHCARD_REVIEW_MEDIUM",
                "value": 5,
                "data_type": "int",
                "description": "Điểm khi ôn thẻ đúng hạn và trả lời trung bình (>=2).",
            },
            {
                "key": "QUIZ_FIRST_TIME_BONUS",
                "value": 5,
                "data_type": "int",
                "description": "Điểm thưởng cho lần đầu làm câu hỏi trắc nghiệm.",
            },
            {
                "key": "QUIZ_CORRECT_BONUS",
                "value": 20,
                "data_type": "int",
                "description": "Điểm thưởng khi trả lời đúng câu hỏi trắc nghiệm.",
            },
            {
                "key": "COURSE_LESSON_COMPLETION_SCORE",
                "value": 15,
                "data_type": "int",
                "description": "Điểm thưởng hoàn thành 1 bài học trong khóa.",
            },
            {
                "key": "COURSE_COMPLETION_SCORE",
                "value": 50,
                "data_type": "int",
                "description": "Điểm thưởng hoàn thành toàn bộ khóa học.",
            },
        ]

    @app.before_request
    def refresh_config_from_db() -> None:  # pragma: no cover - hook
        service.load_settings()

    with app.app_context():
        service.ensure_defaults(_default_settings(app))
        service.load_settings(force=True)

    return service

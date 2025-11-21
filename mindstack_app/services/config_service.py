"""Dịch vụ nạp cấu hình động từ cơ sở dữ liệu."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app, has_app_context

from ..models import SystemSetting


class ConfigService:
    """Đồng bộ cấu hình giữa DB và current_app.config."""

    def __init__(self, app, ttl_seconds: int = 30) -> None:
        self.app = app
        self.ttl_seconds = ttl_seconds
        self._last_loaded: datetime | None = None

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
                return int(raw_value)

            if data_type == "path" and isinstance(raw_value, str):
                return os.path.abspath(raw_value)
        except (TypeError, ValueError):
            current_app.logger.warning(
                "Không thể chuyển đổi giá trị của %s về kiểu %s, dùng giá trị gốc.",
                setting.key,
                data_type,
            )

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

    @app.before_request
    def refresh_config_from_db() -> None:  # pragma: no cover - hook
        service.load_settings()

    with app.app_context():
        service.load_settings(force=True)

    return service

"""Context helpers shared across admin blueprints."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import current_app
from flask_login import current_user

from ...models import ApiKey, BackgroundTask, LearningContainer, SystemSetting, User


def _latest_backup_timestamp() -> str | None:
    """Return the formatted timestamp of the most recent backup, if any."""
    app_root = Path(current_app.root_path)
    backup_dir = app_root / "backups"
    if not backup_dir.exists():
        return None

    backups = list(backup_dir.glob("*.zip"))
    if not backups:
        return None

    latest_file = max(backups, key=lambda file: file.stat().st_mtime)
    timestamp = datetime.fromtimestamp(latest_file.stat().st_mtime)
    return timestamp.strftime("%d/%m/%Y %H:%M")


def build_admin_sidebar_metrics() -> dict[str, Any]:
    """Collect lightweight statistics for the admin chrome."""
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        return {}

    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    total_users = User.query.count()
    active_weekly_users = User.query.filter(User.last_seen.isnot(None)).filter(User.last_seen >= seven_days_ago).count()
    content_total = LearningContainer.query.count()
    active_api_keys = ApiKey.query.filter_by(is_active=True, is_exhausted=False).count()
    running_tasks = BackgroundTask.query.filter_by(status="running").count()

    system_setting = SystemSetting.query.filter_by(key="system_status").first()
    maintenance_mode = False
    if system_setting and isinstance(system_setting.value, dict):
        maintenance_mode = bool(system_setting.value.get("maintenance_mode", False))

    return {
        "total_users": total_users,
        "active_weekly_users": active_weekly_users,
        "content_total": content_total,
        "active_api_keys": active_api_keys,
        "running_tasks": running_tasks,
        "maintenance_mode": maintenance_mode,
        "last_backup": _latest_backup_timestamp(),
    }


def admin_context_processor() -> dict[str, Any]:
    """Inject shared metrics into templates rendered by admin blueprints."""
    return {"admin_sidebar_metrics": build_admin_sidebar_metrics()}

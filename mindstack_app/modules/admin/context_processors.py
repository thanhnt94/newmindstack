# File: mindstack_app/modules/admin/context_processors.py
# Phiên bản: 2.1
# MỤC ĐÍCH: Cập nhật hàm _latest_backup_timestamp để CHỈ đọc đường dẫn từ config.py,
#           loại bỏ code dự phòng (fallback) để đảm bảo đường dẫn luôn đúng.

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import current_app
from flask_login import current_user

from ...config import Config
from ...models import ApiKey, BackgroundTask, LearningContainer, SystemSetting, User
from ...services.config_service import get_runtime_config


def _latest_backup_timestamp() -> str | None:
    """
    Mô tả: Trả về timestamp đã định dạng của bản sao lưu gần đây nhất (nếu có).
    Đọc đường dẫn thư mục sao lưu từ config.
    Returns:
        str | None: Chuỗi thời gian (dd/mm/YYYY HH:MM) hoặc None.
    """
    backup_dir_path = get_runtime_config('BACKUP_FOLDER', Config.BACKUP_FOLDER)
    if not backup_dir_path:
        current_app.logger.warning("BACKUP_FOLDER chưa được cấu hình, không thể tìm backup.")
        return None # Không có thư mục config
        
    backup_dir = Path(backup_dir_path)
    if not backup_dir.exists():
        return None # Thư mục không tồn tại

    # Tìm file zip mới nhất
    try:
        backups = list(backup_dir.glob("*.zip"))
    except OSError as e:
        current_app.logger.error(f"Không thể quét thư mục backup '{backup_dir}': {e}")
        return None
        
    if not backups:
        return None # Không có file sao lưu nào

    latest_file = max(backups, key=lambda file: file.stat().st_mtime)
    timestamp = datetime.fromtimestamp(latest_file.stat().st_mtime)
    return timestamp.strftime("%d/%m/%Y %H:%M")


def build_admin_sidebar_metrics() -> dict[str, Any]:
    """
    Mô tả: Thu thập các số liệu thống kê nhẹ để hiển thị trên sidebar admin.
    Returns:
        dict: Dữ liệu thống kê.
    """
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        return {}

    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    try:
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
            "last_backup": _latest_backup_timestamp(), # Hàm này đã được cập nhật
        }
    except Exception as e:
        # Bắt lỗi nếu DB chưa sẵn sàng hoặc có vấn đề
        current_app.logger.error(f"Lỗi khi xây dựng admin sidebar metrics: {e}")
        return {
            "total_users": "Lỗi",
            "active_weekly_users": "Lỗi",
            "content_total": "Lỗi",
            "active_api_keys": "Lỗi",
            "running_tasks": 0,
            "maintenance_mode": False,
            "last_backup": "N/A",
        }


def admin_context_processor() -> dict[str, Any]:
    """
    Mô tả: Đưa các số liệu thống kê chung vào template của các blueprint admin.
    Returns:
        dict: Dữ liệu để inject vào template context.
    """
    return {"admin_sidebar_metrics": build_admin_sidebar_metrics()}
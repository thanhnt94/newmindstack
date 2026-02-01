# File: mindstack_app/modules/admin/services/settings_service.py
from flask import current_app
from flask_login import current_user
from mindstack_app.core.config import Config
from mindstack_app.services.config_service import SENSITIVE_SETTING_KEYS, get_runtime_config
from mindstack_app.models import AppSettings
import json
import os

# Định nghĩa các cấu hình cốt lõi
CORE_SETTING_FIELDS: list[dict[str, object]] = [
    {
        "key": "ITEMS_PER_PAGE",
        "label": "Số mục trên mỗi trang",
        "data_type": "int",
        "placeholder": "12",
        "description": "Điều chỉnh số lượng bản ghi hiển thị mặc định trong bảng và danh sách.",
        "default": Config.ITEMS_PER_PAGE,
        "group": "system",
    },
    {
        "key": "SYSTEM_TIMEZONE",
        "label": "Múi giờ hệ thống",
        "data_type": "string",
        "placeholder": "UTC",
        "description": "Múi giờ mặc định cho toàn bộ hệ thống (ví dụ: Asia/Ho_Chi_Minh).",
        "default": "UTC",
        "group": "system",
    },
    {
        "key": "NOTIF_SCORE_DURATION",
        "label": "Thời gian hiện điểm (ms)",
        "data_type": "int",
        "placeholder": "1500",
        "description": "Thời gian hiển thị thông báo điểm thưởng (XP) sau mỗi câu trả lời.",
        "default": 1500,
        "group": "notification",
    },
    {
        "key": "NOTIF_SCORE_POSITION",
        "label": "Vị trí hiện điểm",
        "data_type": "string",
        "placeholder": "center",
        "description": "Vị trí thông báo điểm (center, top-center, top-right, bottom-right).",
        "default": "center",
        "group": "notification",
    },
    {
        "key": "NOTIF_STREAK_DURATION",
        "label": "Thời gian hiện Streak (ms)",
        "data_type": "int",
        "placeholder": "2000",
        "description": "Thời gian hiển thị thông báo chuỗi câu trả lời đúng (Streak).",
        "default": 2000,
        "group": "notification",
    },
    {
        "key": "NOTIF_ACHIEVEMENT_DURATION",
        "label": "Thời gian hiện Thành tựu (ms)",
        "data_type": "int",
        "placeholder": "5000",
        "description": "Thời gian hiển thị thông báo mở khóa thành tựu mới.",
        "default": 5000,
        "group": "notification",
    },
]

CORE_SETTING_GROUPS = {
    "system": {
        "label": "Cấu hình chung",
        "icon": "fas fa-cog",
        "description": "Các tham số vận hành cơ bản của hệ thống.",
    },
    "notification": {
        "label": "Thông báo & Hiệu ứng",
        "icon": "fas fa-bell",
        "description": "Điều chỉnh thời gian và vị trí hiển thị các thông báo UI.",
    },
}

CORE_SETTING_KEYS = {field["key"] for field in CORE_SETTING_FIELDS}

SETTING_CATEGORY_LABELS = {
    "paths": "Cấu hình đường dẫn",
    "notification": "Thông báo UI",
    "flashcard": "Điểm flashcard",
    "quiz": "Điểm quiz",
    "course": "Điểm course",
    "other": "Cấu hình khác",
}

def parse_setting_value(raw_value: str | None, data_type: str, *, key: str) -> object:
    """Chuyển đổi giá trị form về đúng kiểu dữ liệu khai báo."""
    normalized_type = (data_type or "string").lower()
    value_to_use = raw_value or ""

    if normalized_type == "bool":
        return str(value_to_use).strip().lower() in {"1", "true", "yes", "on", "bật", "bat"}

    if normalized_type == "int":
        if not value_to_use:
            return 0
        try:
            return int(str(value_to_use).strip())
        except ValueError as exc:
            raise ValueError(f"Giá trị của {key} phải là số nguyên.") from exc

    if normalized_type == "json":
        try:
            return json.loads(value_to_use)
        except json.JSONDecodeError as exc:
            raise ValueError("Định dạng JSON không hợp lệ.") from exc

    if normalized_type == "path":
        return os.path.abspath(value_to_use)

    return value_to_use.strip()

def is_sensitive_setting(key: str) -> bool:
    """Kiểm tra khóa cấu hình có nhạy cảm hay không."""
    return key.upper() in SENSITIVE_SETTING_KEYS

def validate_setting_value(parsed_value: object, data_type: str, *, key: str) -> None:
    """Áp dụng các ràng buộc đơn giản cho giá trị cấu hình."""
    normalized_type = (data_type or "string").lower()

    if normalized_type == "int":
        if isinstance(parsed_value, int) and parsed_value < 0:
            raise ValueError("Giá trị số phải lớn hơn hoặc bằng 0.")

    if normalized_type == "path":
        if not isinstance(parsed_value, str) or not parsed_value:
            raise ValueError("Đường dẫn không được bỏ trống.")

        abs_path = os.path.abspath(parsed_value)
        try:
            os.makedirs(abs_path, exist_ok=True)
        except OSError as exc:
            raise ValueError(
                f"Không thể tạo hoặc truy cập thư mục cho {key}: {abs_path}"
            ) from exc

        if not os.path.isdir(abs_path):
            raise ValueError(f"Đường dẫn không hợp lệ cho {key}: {abs_path}")

        current_app.logger.info("Đảm bảo thư mục tồn tại cho %s: %s", key, abs_path)

def get_core_settings() -> list[dict[str, object]]:
    """Đọc giá trị hiện tại của các cấu hình cốt lõi."""
    resolved_settings: list[dict[str, object]] = []
    for field in CORE_SETTING_FIELDS:
        current_value = get_runtime_config(field["key"], field["default"])
        resolved_settings.append({**field, "value": current_value})
    return resolved_settings

def get_grouped_core_settings() -> dict[str, dict[str, object]]:
    """Nhóm các cấu hình cốt lõi theo group để hiển thị trên UI."""
    grouped: dict[str, dict[str, object]] = {}
    for group_key, group_info in CORE_SETTING_GROUPS.items():
        grouped[group_key] = {
            **group_info,
            "fields": [],
        }

    for field in CORE_SETTING_FIELDS:
        current_value = get_runtime_config(field["key"], field["default"])
        resolved_field = {**field, "value": current_value}
        group_key = field.get("group", "other")
        if group_key in grouped:
            grouped[group_key]["fields"].append(resolved_field)
    return grouped

def refresh_runtime_settings(force: bool = True) -> None:
    """Đồng bộ lại app.config sau khi ghi DB."""
    service = current_app.extensions.get("config_service")
    if service:
        service.load_settings(force=force)

def log_setting_change(action: str, *, key: str, old_value: object, new_value: object) -> None:
    """Ghi nhận log audit cho thay đổi cấu hình."""
    user_label = "anonymous"
    if getattr(current_user, "is_authenticated", False):
        user_label = f"{current_user.username} (id={current_user.user_id})"

    current_app.logger.info(
        "AUDIT CẤU HÌNH - %s bởi %s: %s từ %r thành %r",
        action,
        user_label,
        key,
        old_value,
        new_value,
    )

def categorize_settings(settings: list[AppSettings]) -> dict[str, list[AppSettings]]:
    """Nhóm các cấu hình theo danh mục hiển thị trong giao diện."""
    categories: dict[str, list[AppSettings]] = {
        "paths": [],
        "flashcard": [],
        "quiz": [],
        "course": [],
        "other": [],
    }

    for setting in settings:
        key_upper = setting.key.upper()

        if key_upper.endswith(("_FOLDER", "_PATH", "_DIR", "_DIRECTORY")):
            categories["paths"].append(setting)
            continue

        if key_upper.startswith("FLASHCARD_"):
            categories["flashcard"].append(setting)
            continue

        if key_upper.startswith("QUIZ_"):
            categories["quiz"].append(setting)
            continue

        if key_upper.startswith("COURSE_"):
            categories["course"].append(setting)
            continue

        categories["other"].append(setting)

    return categories

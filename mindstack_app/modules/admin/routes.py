# File: mindstack_app/modules/admin/routes.py
# Phiên bản: 2.8
# MỤC ĐÍCH: Cập nhật hàm _get_backup_folder để CHỈ đọc đường dẫn từ config.py,
#           loại bỏ code dự phòng (fallback) để đảm bảo đường dẫn luôn đúng.
#           Bổ sung chú thích tiếng Việt cho tất cả các hàm.

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
    request,
    current_app,
    send_file,
    after_this_request,
)
from ...core.error_handlers import error_response, success_response
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import or_, nullslast
from ...models import (
    db,
    User,
    LearningContainer,
    LearningGroup,
    LearningItem,
    ContainerContributor,
    ApiKey,
    BackgroundTask,
    BackgroundTaskLog,
    AppSettings,
    UserContainerState,
    UserContainerState,
    LearningProgress, # MIGRATED: Unified progress model
    ScoreLog,
    LearningGoal,
    UserNote,
    UserFeedback,
    # [NEW] Missing models for backup
    LearningSession,
    Badge,
    UserBadge,
    GoalDailyHistory,
    ReviewLog,
    UserItemMarker,
    QuizBattleRoom,
    QuizBattleParticipant,
    QuizBattleRound,
    QuizBattleAnswer,
    QuizBattleMessage,
    FlashcardCollabRoom,
    FlashcardCollabParticipant,
    FlashcardCollabRound,
    FlashcardCollabAnswer,
    FlashcardCollabMessage,
    FlashcardRoomProgress,
)
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm.attributes import flag_modified
import shutil
import os
import zipfile
import io
import json
import csv
import tempfile
from ...utils.template_helpers import render_dynamic_template
from uuid import uuid4
from werkzeug.utils import secure_filename, safe_join
from collections import OrderedDict
from typing import Optional
from sqlalchemy.sql.sqltypes import DateTime, Date, Time
from datetime import date, time

from ...config import Config
# Refactored imports: services now in learning/flashcard/individual/ and learning/quiz/individual/services/
from ..learning.sub_modules.flashcard.services import AudioService, ImageService
from ..learning.sub_modules.quiz.individual.services.audio_service import QuizAudioService
from ..ai_services.ai_explanation_task_service import (
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    generate_ai_explanations,
)
from ..ai_services.gemini_client import GeminiClient
from ..ai_services.huggingface_client import HuggingFaceClient
from ...services.config_service import SENSITIVE_SETTING_KEYS, get_runtime_config

audio_service = AudioService()
image_service = ImageService()
quiz_audio_service = QuizAudioService()

# [NEW] Quiz Config Service
from ...services.quiz_config_service import QuizConfigService
# [NEW] Flashcard Config Service
from ...services.flashcard_config_service import FlashcardConfigService



# [NEW] Quiz Config Service
from ...services.quiz_config_service import QuizConfigService


# Danh mục các gói dữ liệu có thể sao lưu/khôi phục
DATASET_CATALOG: "OrderedDict[str, dict[str, object]]" = OrderedDict(
    {
        'users': {
            'label': 'Người dùng & quản trị viên',
            'description': 'Bao gồm toàn bộ thông tin tài khoản người dùng.',
            'models': [User],
        },
        'content': {
            'label': 'Nội dung học tập (Flashcard, Quiz, Course)',
            'description': 'Tất cả container, nhóm và mục học tập cùng cộng tác viên.',
            'models': [LearningContainer, LearningGroup, LearningItem, ContainerContributor],
        },
        'progress': {
            'label': 'Tiến độ & tương tác học tập',
            'description': 'Bao gồm trạng thái container, tiến độ flashcard/quiz/course, điểm số và ghi chú.',
            'models': [
                UserContainerState,
                LearningProgress, # MIGRATED
                ScoreLog,
                LearningGoal,
                UserNote,
                UserFeedback,
                # [NEW]
                LearningSession,
                ReviewLog,
                UserItemMarker,
                GoalDailyHistory,
                UserBadge,
                Badge,
            ],
        },
        'goals_notes': {
            'label': 'Mục tiêu & ghi chú học tập',
            'description': 'Chỉ bao gồm dữ liệu mục tiêu học tập và ghi chú cá nhân của người học.',
            'models': [LearningGoal, UserNote],
        },
        'system_configs': {
            'label': 'Cấu hình hệ thống & API',
            'description': 'Các thiết lập hệ thống, tác vụ nền và khóa API tích hợp.',
            'models': [AppSettings, BackgroundTask, BackgroundTaskLog, ApiKey],
        },
        'feedback_reports': {
            'label': 'Phản hồi & báo cáo từ người dùng',
            'description': 'Tập trung vào phản hồi, điểm số và lịch sử tương tác phục vụ phân tích.',
            'models': [UserFeedback, ScoreLog],
        },
        'multiplayer': {
            'label': 'Multiplayer (Quiz & Flashcard)',
            'description': 'Dữ liệu các phòng chơi, người tham gia và tin nhắn chat.',
            'models': [
                QuizBattleRoom, QuizBattleParticipant, QuizBattleRound, QuizBattleAnswer, QuizBattleMessage,
                FlashcardCollabRoom, FlashcardCollabParticipant, FlashcardCollabRound, FlashcardCollabAnswer, FlashcardCollabMessage, FlashcardRoomProgress
            ],
        },
    }
)


# Các cấu hình cốt lõi muốn cho phép chỉnh sửa nhanh trên giao diện admin
# Đã gom theo nhóm để UI dễ quản lý hơn
CORE_SETTING_FIELDS: list[dict[str, object]] = [
    # === NHÓM: Đường dẫn hệ thống ===
    # [REMOVED] Hardcoded in Config, hidden from Admin UI
    # === NHÓM: Cấu hình chung ===
    # === NHÓM: Cấu hình chung ===
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
]

# Định nghĩa các nhóm settings để hiển thị trên UI
CORE_SETTING_GROUPS = {
    # "paths": {
    #     "label": "Đường dẫn hệ thống",
    #     "icon": "fas fa-folder-open",
    #     "description": "Cấu hình các thư mục lưu trữ file của hệ thống.",
    # },
    "system": {
        "label": "Cấu hình chung",
        "icon": "fas fa-cog",
        "description": "Các tham số vận hành cơ bản của hệ thống.",
    },
}

CORE_SETTING_KEYS = {field["key"] for field in CORE_SETTING_FIELDS}

SETTING_CATEGORY_LABELS = {
    "paths": "Cấu hình đường dẫn",
    "flashcard": "Điểm flashcard",
    "quiz": "Điểm quiz",
    "course": "Điểm course",
    "other": "Cấu hình khác",
}


def _resolve_database_path():
    """
    Mô tả: Xác định đường dẫn tuyệt đối đến file cơ sở dữ liệu SQLite.
    Returns:
        str: Đường dẫn file.
    Raises:
        RuntimeError: Nếu URI không được cấu hình hoặc không phải là SQLite.
    """
    uri = get_runtime_config('SQLALCHEMY_DATABASE_URI', Config.SQLALCHEMY_DATABASE_URI)
    if not uri:
        raise RuntimeError('Hệ thống chưa cấu hình kết nối cơ sở dữ liệu.')
    if uri.startswith('sqlite:///'):
        return uri.replace('sqlite:///', '')
    raise RuntimeError('Chức năng sao lưu hiện chỉ hỗ trợ cơ sở dữ liệu SQLite.')


def _get_backup_folder():
    """
    Mô tả: Lấy đường dẫn thư mục sao lưu từ file config (đã cấu hình trong config.py).
    Đảm bảo thư mục tồn tại.
    Returns:
        str: Đường dẫn thư mục sao lưu.
    Raises:
        RuntimeError: Nếu biến BACKUP_FOLDER không được cấu hình trong config.py.
    """
    backup_folder = Config.BACKUP_FOLDER
    if not backup_folder:
        # Nếu config.py không định nghĩa, đây là một lỗi nghiêm trọng
        current_app.logger.error("LỖI CẤU HÌNH: BACKUP_FOLDER không được định nghĩa trong config.py.")
        raise RuntimeError("Lỗi cấu hình: BACKUP_FOLDER chưa được thiết lập.")
    
    # Đảm bảo thư mục tồn tại (config.py đã làm, nhưng an toàn)
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder


def _parse_setting_value(raw_value: str | None, data_type: str, *, key: str) -> object:
    """
    Chuyển đổi giá trị form về đúng kiểu dữ liệu khai báo.
    """

    normalized_type = (data_type or "string").lower()
    value_to_use = raw_value or ""

    if normalized_type == "bool":
        return str(value_to_use).strip().lower() in {"1", "true", "yes", "on", "bật", "bat"}

    if normalized_type == "int":
        if not value_to_use:
            return 0
        try:
            return int(str(value_to_use).strip())
        except ValueError as exc:  # pragma: no cover - validation
            raise ValueError(f"Giá trị của {key} phải là số nguyên.") from exc

    if normalized_type == "json":
        try:
            return json.loads(value_to_use)
        except json.JSONDecodeError as exc:  # pragma: no cover - validation
            raise ValueError("Định dạng JSON không hợp lệ.") from exc

    if normalized_type == "path":
        return os.path.abspath(value_to_use)

    return value_to_use.strip()


def _is_sensitive_setting(key: str) -> bool:
    """Kiểm tra khóa cấu hình có nhạy cảm hay không."""

    return key.upper() in SENSITIVE_SETTING_KEYS


def _validate_setting_value(parsed_value: object, data_type: str, *, key: str) -> None:
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
        except OSError as exc:  # pragma: no cover - phụ thuộc môi trường
            raise ValueError(
                f"Không thể tạo hoặc truy cập thư mục cho {key}: {abs_path}"
            ) from exc

        if not os.path.isdir(abs_path):
            raise ValueError(f"Đường dẫn không hợp lệ cho {key}: {abs_path}")

        current_app.logger.info("Đảm bảo thư mục tồn tại cho %s: %s", key, abs_path)


def _get_core_settings() -> list[dict[str, object]]:
    """Đọc giá trị hiện tại của các cấu hình cốt lõi."""

    resolved_settings: list[dict[str, object]] = []
    for field in CORE_SETTING_FIELDS:
        current_value = get_runtime_config(field["key"], field["default"])
        resolved_settings.append({**field, "value": current_value})

    return resolved_settings


def _get_grouped_core_settings() -> dict[str, dict[str, object]]:
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


def _refresh_runtime_settings(force: bool = True) -> None:
    """Đồng bộ lại app.config sau khi ghi DB."""

    service = current_app.extensions.get("config_service")
    if service:
        service.load_settings(force=force)


def _log_setting_change(action: str, *, key: str, old_value: object, new_value: object) -> None:
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


def _categorize_settings(settings: list[AppSettings]) -> dict[str, list[AppSettings]]:
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


def _serialize_instance(instance):
    """
    Mô tả: Chuyển đổi một đối tượng model SQLAlchemy thành dictionary.
    Args:
        instance: Đối tượng model (ví dụ: User, LearningContainer).
    Returns:
        dict: Dữ liệu của đối tượng dưới dạng dictionary.
    """
    data: dict[str, object] = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        # Xử lý các kiểu dữ liệu đặc biệt (datetime, date, time)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif isinstance(value, date):
            data[column.name] = value.isoformat()
        elif isinstance(value, time):
            data[column.name] = value.isoformat()
        else:
            data[column.name] = value
    return data


def _coerce_column_value(column, value):
    """
    Mô tả: Chuyển đổi giá trị (thường là từ JSON) về đúng kiểu dữ liệu của cột DB.
    Args:
        column: Cột SQLAlchemy.
        value: Giá trị cần chuyển đổi.
    Returns:
        Giá trị đã được chuyển đổi (ví dụ: chuỗi ISO -> đối tượng datetime).
    """
    if value is None:
        return None

    column_type = column.type
    try:
        # Chuyển đổi các chuỗi thời gian về lại đối tượng
        if isinstance(column_type, DateTime):
            if isinstance(value, str):
                return datetime.fromisoformat(value)
        elif isinstance(column_type, Date):
            if isinstance(value, str):
                return date.fromisoformat(value)
        elif isinstance(column_type, Time):
            if isinstance(value, str):
                return time.fromisoformat(value)
    except ValueError:
        return value # Trả về giá trị gốc nếu không thể chuyển đổi
    return value


def _collect_dataset_payload(dataset_key):
    """
    Mô tả: Thu thập toàn bộ dữ liệu từ các bảng được định nghĩa trong DATASET_CATALOG.
    Args:
        dataset_key (str): Tên của gói dataset (ví dụ: 'users', 'content').
    Returns:
        dict: Một dictionary với key là tên bảng và value là danh sách các record.
    """
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')

    payload: dict[str, list[dict[str, object]]] = {}
    for model in config['models']:
        # Lấy tất cả bản ghi và sắp xếp theo khóa chính để đảm bảo thứ tự
        rows = model.query.order_by(*model.__table__.primary_key.columns).all()
        payload[model.__tablename__] = [_serialize_instance(row) for row in rows]
    return payload


def _write_dataset_to_zip(zipf, dataset_key, payload):
    """
    Mô tả: Ghi dữ liệu payload của một dataset vào file zip.
    Ghi cả manifest.json, file .json và file .csv cho mỗi bảng.
    Args:
        zipf (zipfile.ZipFile): Đối tượng file zip đang mở.
        dataset_key (str): Tên của dataset.
        payload (dict): Dữ liệu đã được thu thập từ _collect_dataset_payload.
    """
    manifest = {
        'type': 'dataset',
        'dataset': dataset_key,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'tables': list(payload.keys()),
    }
    # Ghi file manifest
    zipf.writestr(f'{dataset_key}/manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    for table_name, records in payload.items():
        # Ghi file JSON
        json_bytes = json.dumps(records, ensure_ascii=False, indent=2).encode('utf-8')
        zipf.writestr(f'{dataset_key}/{table_name}.json', json_bytes)

        # Ghi file CSV (nếu có dữ liệu)
        if records:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
            zipf.writestr(f'{dataset_key}/{table_name}.csv', output.getvalue())


def _read_backup_manifest(zipf):
    """
    Mô tả: Đọc file manifest.json từ một file zip.
    Args:
        zipf (zipfile.ZipFile): Đối tượng file zip.
    Returns:
        tuple: (dữ liệu manifest, đường dẫn manifest) hoặc (None, None).
    """
    # Các đường dẫn manifest có thể
    candidates = ['manifest.json']
    candidates.extend(name for name in zipf.namelist() if name.endswith('/manifest.json'))

    for candidate in candidates:
        try:
            raw = zipf.read(candidate)
        except KeyError:
            continue # Thử file tiếp theo

        try:
            # Trả về dữ liệu JSON và đường dẫn đã tìm thấy
            return json.loads(raw.decode('utf-8')), candidate
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue # File hỏng, thử file tiếp theo

    return None, None # Không tìm thấy manifest


def _extract_dataset_payload_from_zip(zipf, dataset_key):
    """
    Mô tả: Trích xuất dữ liệu (payload) từ file zip dựa trên dataset_key.
    Args:
        zipf (zipfile.ZipFile): Đối tượng file zip.
        dataset_key (str): Tên dataset (ví dụ: 'content').
    Returns:
        dict: Payload dữ liệu (giống _collect_dataset_payload).
    """
    payload: dict[str, list[dict[str, object]]] = {}
    members = set(zipf.namelist()) # Danh sách các file trong zip

    # Duyệt qua các model trong dataset
    for model in DATASET_CATALOG[dataset_key]['models']:
        table_name = model.__tablename__
        # Thử tìm file json (cả có tiền tố thư mục hoặc không)
        for candidate in (f'{dataset_key}/{table_name}.json', f'{table_name}.json'):
            if candidate not in members:
                continue # Thử tên file tiếp theo

            try:
                # Đọc và parse file JSON
                data = json.loads(zipf.read(candidate).decode('utf-8'))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                continue # File lỗi, bỏ qua

            if isinstance(data, list):
                payload[table_name] = data
            break # Đã tìm thấy file cho bảng này

    return payload


def _infer_dataset_key_from_zip(zipf):
    """
    Mô tả: Đoán dataset_key từ nội dung file zip (nếu manifest thiếu).
    Args:
        zipf (zipfile.ZipFile): Đối tượng file zip.
    Returns:
        str | None: Tên dataset_key đoán được.
    """
    members = set(zipf.namelist())
    best_match: tuple[Optional[str], int] = (None, 0) # (key, số bảng)

    # Duyệt qua tất cả các dataset
    for dataset_key, config in DATASET_CATALOG.items():
        table_names = {model.__tablename__ for model in config['models']}
        # Tìm các file json có trong zip
        available = {
            table_name
            for table_name in table_names
            if f'{dataset_key}/{table_name}.json' in members or f'{table_name}.json' in members
        }

        if not available:
            continue # Dataset này không có file nào

        if not available.issubset(table_names):
            continue # Tên file lạ, không khớp

        # Chọn dataset nào có ít bảng nhất mà vẫn khớp
        if best_match[0] is None or len(table_names) < best_match[1]:
            best_match = (dataset_key, len(table_names))

    return best_match[0]


def _infer_dataset_key_from_json(data):
    """
    Mô tả: Đoán dataset_key từ file JSON (nếu người dùng tải lên file .json).
    Args:
        data (dict): Dữ liệu JSON đã parse.
    Returns:
        str | None: Tên dataset_key đoán được.
    """
    available_tables = {key for key, value in data.items() if isinstance(value, list)}
    if not available_tables:
        return None

    best_match: tuple[Optional[str], int] = (None, 0)

    # Logic tương tự _infer_dataset_key_from_zip
    for dataset_key, config in DATASET_CATALOG.items():
        table_names = {model.__tablename__ for model in config['models']}
        if not available_tables.issubset(table_names):
            continue
        if best_match[0] is None or len(table_names) < best_match[1]:
            best_match = (dataset_key, len(table_names))

    return best_match[0]


def _restore_backup_from_zip(zipf, restore_database=True, restore_uploads=True):
    """
    Mô tả: Ghi đè database và/hoặc thư mục uploads từ file zip.
    Args:
        zipf (zipfile.ZipFile): Đối tượng file zip.
        restore_database (bool): Có ghi đè database không.
        restore_uploads (bool): Có ghi đè thư mục uploads không.
    """
    members = zipf.namelist()

    db_path: Optional[str] = None
    if restore_database:
        # Đóng kết nối DB hiện tại
        db.session.close()
        db.engine.dispose()
        db_path = _resolve_database_path()

    temp_dir = tempfile.mkdtemp(prefix='mindstack_restore_')

    try:
        if restore_database:
            if not db_path:
                raise RuntimeError('Không thể xác định đường dẫn cơ sở dữ liệu để khôi phục.')

            # Tìm file database trong zip
            db_basename = os.path.basename(db_path)
            db_member = next((m for m in members if os.path.basename(m) == db_basename), None)
            if not db_member:
                raise RuntimeError('Gói sao lưu không chứa file cơ sở dữ liệu hợp lệ.')

            # Giải nén và ghi đè
            zipf.extract(db_member, temp_dir)
            extracted_db_path = os.path.join(temp_dir, db_member)
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            shutil.copy2(extracted_db_path, db_path)

        if restore_uploads:
            uploads_folder = Config.UPLOAD_FOLDER
            # Kiểm tra xem zip có thư mục uploads không
            if uploads_folder and any(member.startswith('uploads/') for member in members):
                zipf.extractall(temp_dir)
                source_uploads = os.path.join(temp_dir, 'uploads')
                if os.path.exists(source_uploads):
                    # Xóa thư mục uploads cũ và copy thư mục mới
                    shutil.rmtree(uploads_folder, ignore_errors=True)
                    shutil.copytree(source_uploads, uploads_folder, dirs_exist_ok=True)
    finally:
        # Dọn dẹp thư mục tạm
        shutil.rmtree(temp_dir, ignore_errors=True)


def _restore_from_uploaded_bytes(raw_bytes, dataset_hint=None):
    """
    Mô tả: Xử lý file (zip hoặc json) người dùng tải lên để khôi phục.
    Args:
        raw_bytes (bytes): Nội dung file.
        dataset_hint (str | None): Gợi ý loại dataset (nếu có).
    Returns:
        tuple: (loại khôi phục, dataset_key nếu có).
    """
    if not raw_bytes:
        raise ValueError('File tải lên rỗng.')

    buffer = io.BytesIO(raw_bytes)

    if zipfile.is_zipfile(buffer):
        # Xử lý file ZIP
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as zipf:
            manifest_data, _ = _read_backup_manifest(zipf)

            manifest_type = manifest_data.get('type') if isinstance(manifest_data, dict) else None

            # Khôi phục toàn bộ
            if manifest_type == 'full':
                includes_uploads = bool(manifest_data.get('includes_uploads', False))
                _restore_backup_from_zip(zipf, restore_database=True, restore_uploads=includes_uploads)
                return 'full', None

            # Khôi phục chỉ database
            if manifest_type == 'database':
                _restore_backup_from_zip(zipf, restore_database=True, restore_uploads=False)
                return 'database', None

            # Khôi phục 1 phần (dataset)
            dataset_key = None
            if dataset_hint and dataset_hint in DATASET_CATALOG:
                dataset_key = dataset_hint
            elif manifest_data and isinstance(manifest_data, dict):
                manifest_dataset = manifest_data.get('dataset')
                if isinstance(manifest_dataset, str) and manifest_dataset in DATASET_CATALOG:
                    dataset_key = manifest_dataset

            if not dataset_key:
                dataset_key = _infer_dataset_key_from_zip(zipf)

            if dataset_key:
                payload = _extract_dataset_payload_from_zip(zipf, dataset_key)
                if not payload:
                    raise ValueError('Không tìm thấy dữ liệu hợp lệ trong gói sao lưu.')
                _apply_dataset_restore(dataset_key, payload)
                return 'dataset', dataset_key

        raise ValueError('Không thể xác định loại gói sao lưu từ file ZIP đã tải lên.')

    # Xử lý file JSON (cho dataset)
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('File tải lên không phải là file ZIP hoặc JSON hợp lệ.') from exc

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('Định dạng JSON không hợp lệ. Hãy tải lên file JSON chứa dữ liệu bảng.')

    dataset_key = None
    if dataset_hint and dataset_hint in DATASET_CATALOG:
        dataset_key = dataset_hint
    else:
        dataset_key = _infer_dataset_key_from_json(data)

    if not dataset_key:
        raise ValueError('Không thể xác định dataset phù hợp cho dữ liệu đã tải lên.')

    payload = {table: records for table, records in data.items() if isinstance(records, list)}
    if not payload:
        raise ValueError('Không tìm thấy dữ liệu hợp lệ trong file JSON đã tải lên.')

    _apply_dataset_restore(dataset_key, payload)
    return 'dataset', dataset_key


def _apply_dataset_restore(dataset_key, payload):
    """
    Mô tả: Áp dụng khôi phục một phần (dataset) vào database.
    Xóa dữ liệu cũ trong các bảng liên quan và chèn dữ liệu mới.
    Args:
        dataset_key (str): Tên dataset (ví dụ: 'content').
        payload (dict): Dữ liệu (từ file zip hoặc json).
    """
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')

    # SỬA LỖI: Thay thế 'if db.session.in_transaction():' bằng 'if db.session.is_active:'
    if db.session.is_active:
        db.session.rollback()

    # Bắt đầu một giao dịch mới
    with db.session.begin():
        # Xóa dữ liệu cũ (theo thứ tự ngược lại để tránh lỗi khóa ngoại)
        for model in reversed(config['models']):
            db.session.execute(db.delete(model))

        # Thêm dữ liệu mới
        for model in config['models']:
            records = payload.get(model.__tablename__, [])
            if not records:
                continue
            for record in records:
                instance = model()
                # Duyệt qua các cột và gán dữ liệu, chuyển đổi kiểu nếu cần
                for column in model.__table__.columns:
                    if column.name not in record:
                        continue
                    setattr(instance, column.name, _coerce_column_value(column, record[column.name]))
                db.session.add(instance)

# --- Các route (tuyến đường) ---

from . import admin_bp  # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.
from .context_processors import build_admin_sidebar_metrics

ADMIN_ALLOWED_MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.opus',
    '.mp4', '.webm', '.mov', '.mkv', '.avi', '.m4v',
    '.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.txt', '.zip', '.rar', '.7z', '.json'
}


def _format_file_size(num_bytes):
    """
    Mô tả: Định dạng kích thước file (bytes) thành chuỗi dễ đọc (KB, MB, GB).
    Args:
        num_bytes (int): Kích thước file (bytes).
    Returns:
        str: Chuỗi đã định dạng.
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB" # Fallback


def _normalize_subpath(path_value):
    """
    Mô tả: Chuẩn hóa đường dẫn thư mục con, loại bỏ các ký tự nguy hiểm.
    Args:
        path_value (str | None): Đường dẫn thô.
    Returns:
        str: Đường dẫn đã chuẩn hóa (an toàn).
    """
    normalized = os.path.normpath(path_value or '').replace('\\', '/')
    if normalized in ('', '.', '/'): # Thư mục gốc
        return ''
    if normalized.startswith('..'):
        raise ValueError('Đường dẫn không hợp lệ.')
    return normalized.strip('/')


def _collect_directory_listing(base_dir, upload_root):
    """
    Mô tả: Lấy danh sách các thư mục và file trong một thư mục.
    Args:
        base_dir (str): Đường dẫn thư mục cần quét.
        upload_root (str): Đường dẫn gốc của thư mục uploads.
    Returns:
        tuple: (danh sách thư mục, danh sách file).
    """
    directories = []
    files = []

    if not os.path.isdir(base_dir):
        return directories, files

    # Quét các mục trong thư mục
    for entry in os.scandir(base_dir):
        if entry.name.startswith('.'):
            continue # Bỏ qua file/thư mục ẩn
        relative = os.path.relpath(entry.path, upload_root).replace('\\', '/')
        if entry.is_dir():
            # Nếu là thư mục
            directories.append({
                'name': entry.name,
                'path': relative.strip('/'),
                'item_count': sum(1 for _ in os.scandir(entry.path)) if os.path.isdir(entry.path) else 0,
                'modified': datetime.fromtimestamp(entry.stat().st_mtime)
            })
        elif entry.is_file():
            # Nếu là file
            stat = entry.stat()
            files.append({
                'name': entry.name,
                'path': relative,
                'url': url_for('static', filename=relative),
                'size': _format_file_size(stat.st_size),
                'size_bytes': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'extension': os.path.splitext(entry.name)[1].lower()
            })

    # Sắp xếp
    directories.sort(key=lambda item: item['name'].lower())
    files.sort(key=lambda item: item['modified'], reverse=True)
    return directories, files

# Middleware để kiểm tra quyền admin cho toàn bộ Blueprint admin
@admin_bp.before_request 
def admin_required():
    """
    Mô tả: Middleware (bộ lọc) chạy trước mọi request vào admin_bp.
    Đảm bảo chỉ người dùng có vai trò 'admin' mới được truy cập.
    """
    # Whitelist login route & static files if needed
    if request.endpoint == 'admin.login':
        return

    # If not logged in, redirect to ADMIN login, not standard login
    if not current_user.is_authenticated:
        return redirect(url_for('admin.login', next=request.url))

    # If logged in but not admin, also redirect to Admin Login (effectively logout from admin perspective)
    if current_user.is_authenticated and current_user.user_role != User.ROLE_ADMIN:
        # Optional: Flash message explaining why
        flash('Vui lòng đăng nhập với tài khoản Admin.', 'warning')
        return redirect(url_for('admin.login', next=request.url))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Separate login route for Administrators."""
    if current_user.is_authenticated:
        if current_user.user_role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        
        # If logged in as User but requesting Admin Login, auto-logout the User session
        # so they can see the Admin Login form.
        from flask_login import logout_user
        logout_user()
        flash('Đã đăng xuất tài khoản thường. Vui lòng đăng nhập Admin.', 'info')
    
    # Use dedicated AdminLoginForm from local forms module
    from .forms import AdminLoginForm
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Admin ID hoặc Security Key không đúng.', 'danger')
            return redirect(url_for('admin.login'))
        
        # Enforce Admin Role
        if user.user_role != 'admin':
            flash('Truy cập bị từ chối: Tài khoản này không có quyền Quản trị.', 'danger')
            return redirect(url_for('admin.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            from mindstack_app.modules.gamification.services.scoring_service import ScoreService
            ScoreService.record_daily_login(user.user_id)
        except Exception:
            pass

        flash('Chào mừng Quản trị viên! Đã truy cập hệ thống an toàn.', 'success')
        # Check 'next' parameter safely
        next_page = request.args.get('next')
        if not next_page or url_for(next_page.lstrip('/')) == url_for('landing.index'):
            next_page = url_for('admin.admin_dashboard')
        return redirect(next_page)
        
    # Use standard render_template for Admin Login (independent of v3/v4 user themes)
    return render_template('admin/login.html', form=form)

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def admin_dashboard():
    """
    Mô tả: Hiển thị trang dashboard admin tổng quan.
    """
    # Lấy các chỉ số thống kê
    total_users = db.session.query(User).count()
    users_last_24h = db.session.query(User).filter(User.last_seen >= (datetime.utcnow() - timedelta(hours=24))).count()
    
    total_containers = db.session.query(LearningContainer).count()
    total_items = db.session.query(LearningItem).count()
    
    active_api_keys = db.session.query(ApiKey).filter_by(is_active=True, is_exhausted=False).count()
    exhausted_api_keys = db.session.query(ApiKey).filter_by(is_exhausted=True).count()
    
    # Tạo một dictionary chứa các dữ liệu thống kê
    stats_data = {
        'total_users': total_users,
        'users_last_24h': users_last_24h,
        'total_containers': total_containers,
        'total_items': total_items,
        'active_api_keys': active_api_keys,
        'exhausted_api_keys': exhausted_api_keys
    }

    # Lấy 5 người dùng hoạt động gần nhất
    recent_users = (
        User.query.filter(User.last_seen.isnot(None))
        .order_by(User.last_seen.desc())
        .limit(5)
        .all()
    )

    # Lấy 5 bộ học liệu mới tạo gần nhất
    recent_containers = (
        LearningContainer.query.order_by(LearningContainer.created_at.desc())
        .limit(5)
        .all()
    )

    # Lấy các tác vụ nền
    recent_tasks = (
        BackgroundTask.query.order_by(nullslast(BackgroundTask.last_updated.desc()))
        .limit(4)
        .all()
    )

    # Lấy các chỉ số chung cho sidebar (từ context processor)
    overview_metrics = build_admin_sidebar_metrics()

    return render_template(
        'admin/dashboard.html',
        stats_data=stats_data,
        recent_users=recent_users,
        recent_containers=recent_containers,
        recent_tasks=recent_tasks,
        overview_metrics=overview_metrics,
    )


@admin_bp.route('/media-library', methods=['GET', 'POST'])
def media_library():
    """
    Mô tả: Hiển thị trang quản lý thư viện media (tải file, tạo thư mục).
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        # Lấy thư mục hiện tại (từ form post hoặc query param)
        current_folder = _normalize_subpath(
            request.form.get('current_folder') if request.method == 'POST' else request.args.get('folder')
        )
    except ValueError:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    # Xác định đường dẫn tuyệt đối an toàn
    target_dir = safe_join(upload_root, current_folder) if current_folder else upload_root
    if target_dir is None:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    os.makedirs(target_dir, exist_ok=True)

    if request.method == 'POST':
        action = request.form.get('action', 'upload')
        if action == 'create_folder':
            # Xử lý tạo thư mục mới
            new_folder_name = secure_filename(request.form.get('folder_name', '').strip())
            if not new_folder_name:
                flash('Tên thư mục không hợp lệ.', 'warning')
            else:
                new_dir = os.path.join(target_dir, new_folder_name)
                os.makedirs(new_dir, exist_ok=True)
                flash(f'Đã tạo thư mục "{new_folder_name}".', 'success')
                normalized_new_dir = _normalize_subpath(os.path.relpath(new_dir, upload_root))
                return redirect(url_for('admin.media_library', folder=normalized_new_dir))
        else:
            # Xử lý tải file lên
            uploaded_files = request.files.getlist('media_files')
            if not uploaded_files:
                flash('Vui lòng chọn ít nhất một file để tải lên.', 'warning')
            else:
                saved = []
                skipped = []
                for file in uploaded_files:
                    if not file or file.filename == '':
                        continue
                    original_name = file.filename
                    filename = secure_filename(original_name)
                    if not filename:
                        skipped.append(original_name)
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext and ext not in ADMIN_ALLOWED_MEDIA_EXTENSIONS:
                        skipped.append(original_name)
                        continue

                    # Xử lý trùng tên file
                    candidate_name = filename
                    destination = os.path.join(target_dir, candidate_name)
                    while os.path.exists(destination):
                        name_part, extension_part = os.path.splitext(filename)
                        candidate_name = f"{name_part}_{uuid4().hex[:6]}{extension_part}"
                        destination = os.path.join(target_dir, candidate_name)

                    try:
                        file.save(destination)
                        saved.append(candidate_name)
                    except Exception as exc:
                        current_app.logger.exception('Không thể lưu file %s: %s', candidate_name, exc)
                        skipped.append(original_name)

                if saved:
                    flash(f'Đã tải lên {len(saved)} file thành công.', 'success')
                if skipped:
                    flash('Một số file bị bỏ qua: ' + ', '.join(skipped), 'warning')

        return redirect(url_for('admin.media_library', folder=current_folder or None))

    # Xử lý GET request (hiển thị file/thư mục)
    directories, files = _collect_directory_listing(target_dir, upload_root)
    breadcrumb = []
    if current_folder:
        parts = current_folder.split('/')
        cumulative = []
        for part in parts:
            cumulative.append(part)
            breadcrumb.append({'name': part, 'path': '/'.join(cumulative)})

    parent_folder = '/'.join(current_folder.split('/')[:-1]) if current_folder else ''
    total_size = _format_file_size(sum(item['size_bytes'] for item in files)) if files else '0 B'

    return render_template(
        'admin/media_library.html',
        directories=directories,
        files=files,
        current_folder=current_folder,
        parent_folder=parent_folder,
        breadcrumb=breadcrumb,
        total_size=total_size,
    )


@admin_bp.route('/media-library/delete', methods=['POST'])
def delete_media_item():
    """
    Mô tả: Xử lý yêu cầu xóa một file media.
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        relative_path = _normalize_subpath(request.form.get('path'))
    except ValueError:
        flash('Đường dẫn file không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    full_path = safe_join(upload_root, relative_path)
    if not full_path or not os.path.isfile(full_path):
        flash('Không tìm thấy file để xóa.', 'warning')
        parent_folder = '/'.join((relative_path or '').split('/')[:-1])
        return redirect(url_for('admin.media_library', folder=parent_folder or None))

    try:
        os.remove(full_path)
        flash('Đã xóa file thành công.', 'success')
    except Exception as exc:
        current_app.logger.exception('Không thể xóa file %s: %s', full_path, exc)
        flash('Không thể xóa file. Vui lòng thử lại.', 'danger')

    parent_folder = '/'.join(relative_path.split('/')[:-1])
    return redirect(url_for('admin.media_library', folder=parent_folder or None))


@admin_bp.route('/voice-service')
@login_required
def voice_service_panel():
    """
    Mô tả: Hiển thị trang quản lý Voice Service: tạo audio cho flashcard, dọn dẹp cache.
    """
    # Lấy các tác vụ liên quan đến audio
    voice_task_names = ['generate_audio_cache', 'clean_audio_cache', 'transcribe_quiz_audio']
    
    # Ensure tasks exist
    for t_name in voice_task_names:
        if not BackgroundTask.query.filter_by(task_name=t_name).first():
            new_task = BackgroundTask(task_name=t_name, status='idle')
            db.session.add(new_task)
    db.session.commit()

    tasks = BackgroundTask.query.filter(BackgroundTask.task_name.in_(voice_task_names)).all()
    
    flashcard_containers = (
        LearningContainer.query.filter_by(container_type='FLASHCARD_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    quiz_containers = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )
    
    return render_template(
        'admin/voice_service_panel.html',
        tasks=tasks,
        flashcard_containers=flashcard_containers,
        quiz_containers=quiz_containers
    )

@admin_bp.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền (ví dụ: tạo cache audio).
    """
    tasks = BackgroundTask.query.all()
    # Đảm bảo các tác vụ mong muốn tồn tại trong DB
    desired_tasks = [
        'generate_audio_cache',
        'clean_audio_cache',
        'generate_image_cache',
        'clean_image_cache',
        'generate_ai_explanations'
    ]
    created_any = False
    for task_name in desired_tasks:
        if not BackgroundTask.query.filter_by(task_name=task_name).first():
            db.session.add(BackgroundTask(task_name=task_name, message='Sẵn sàng', is_enabled=True))
            created_any = True
    if created_any:
        db.session.commit()
        tasks = BackgroundTask.query.all()

    # Lấy danh sách học liệu để lọc phạm vi (Flashcard & Quiz)
    flashcard_containers = (
        LearningContainer.query.filter_by(container_type='FLASHCARD_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )
    quiz_containers = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    return render_template(
        'admin/background_tasks.html',
        tasks=tasks,
        flashcard_containers=flashcard_containers,
        quiz_containers=quiz_containers,
        default_request_interval=DEFAULT_REQUEST_INTERVAL_SECONDS,
    )


def _serialize_task_log(log: BackgroundTaskLog) -> dict[str, object]:
    return {
        'log_id': log.log_id,
        'status': log.status,
        'progress': log.progress,
        'total': log.total,
        'message': log.message,
        'stop_requested': log.stop_requested,
        'created_at': log.created_at.isoformat() if log.created_at else None,
    }

@admin_bp.route('/tasks/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """
    Mô tả: Bật/tắt một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    task.is_enabled = not task.is_enabled
    db.session.commit()
    return success_response(data={'is_enabled': task.is_enabled})

@admin_bp.route('/tasks/start/<int:task_id>', methods=['POST'])
def start_task(task_id):
    """
    Mô tả: Bắt đầu một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status == 'running':
        return error_response('Tác vụ đang chạy, vui lòng dừng trước khi khởi động lại.', 'CONFLICT', 409)

    if not task.is_enabled:
        return error_response('Tác vụ đang bị tắt, hãy bật công tắc trước khi bắt đầu.', 'BAD_REQUEST', 400)

    data = request.get_json(silent=True) or {}
    container_id = data.get('container_id') if isinstance(data, dict) else None
    container_type = data.get('container_type') if isinstance(data, dict) else None
    try:
        delay_seconds = float(data.get('request_interval_seconds', DEFAULT_REQUEST_INTERVAL_SECONDS))
        if delay_seconds < 0:
            delay_seconds = 0
    except (TypeError, ValueError):
        delay_seconds = DEFAULT_REQUEST_INTERVAL_SECONDS
    container_scope_ids = None
    scope_label = 'tất cả bộ học liệu'

    if container_id not in (None, ''):
        try:
            container_id_int = int(container_id)
        except (TypeError, ValueError):
            return error_response('Giá trị container_id không hợp lệ.', 'BAD_REQUEST', 400)

        query = LearningContainer.query.filter_by(container_id=container_id_int)
        if container_type:
            query = query.filter_by(container_type=container_type)

        selected_container = query.first()
        if not selected_container:
            return error_response('Không tìm thấy học liệu được chọn.', 'NOT_FOUND', 404)

        container_scope_ids = [selected_container.container_id]
        type_labels = {
            'FLASHCARD_SET': 'bộ thẻ',
            'QUIZ_SET': 'bộ Quiz',
        }
        type_label = type_labels.get(selected_container.container_type, 'bộ học liệu')
        scope_label = f"{type_label} \"{selected_container.title}\" (ID {selected_container.container_id})"

    if task.task_name == 'generate_ai_explanations' and scope_label == 'tất cả bộ học liệu':
        scope_label = 'tất cả học liệu'

    task.status = 'running'
    task.message = f"Đang khởi chạy cho {scope_label}..."
    db.session.commit()

    # Chạy tác vụ (hiện tại là đồng bộ, nên nâng cấp lên thread/process)
    if task.task_name == 'generate_audio_cache':
        audio_service.generate_cache_for_all_cards(task, container_ids=container_scope_ids)
    elif task.task_name == 'clean_audio_cache':
        audio_service.clean_orphan_audio_cache(task)
    elif task.task_name == 'transcribe_quiz_audio':
        quiz_audio_service.transcribe_quiz_audio(task, container_ids=container_scope_ids)
    elif task.task_name == 'generate_image_cache':
        asyncio.run(image_service.generate_images_for_missing_cards(task, container_ids=container_scope_ids))
    elif task.task_name == 'clean_image_cache':
        image_service.clean_orphan_image_cache(task)
    elif task.task_name == 'generate_ai_explanations':
        scope_label = (
            'tất cả học liệu' if not container_scope_ids else 'các bộ học liệu đã chọn'
        )
        generate_ai_explanations(
            task,
            container_ids=container_scope_ids,
            delay_seconds=delay_seconds,
        )

    return success_response(data={'scope_label': scope_label})

@admin_bp.route('/tasks/stop/<int:task_id>', methods=['POST'])
def stop_task(task_id):
    """
    Mô tả: Dừng một tác vụ nền đang chạy.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status == 'running':
        task.stop_requested = True
        task.message = 'Đã nhận yêu cầu dừng, sẽ kết thúc sau bước hiện tại.'
        db.session.commit()
        return success_response(message='Yêu cầu dừng đã được gửi.')
    return error_response('Tác vụ không chạy.', 'BAD_REQUEST', 400)


@admin_bp.route('/tasks/<int:task_id>/logs', methods=['GET'])
def view_task_logs(task_id: int):
    """Hiển thị log chi tiết cho một tác vụ nền."""

    task = BackgroundTask.query.get_or_404(task_id)
    logs = (
        BackgroundTaskLog.query.filter_by(task_id=task_id)
        .order_by(BackgroundTaskLog.created_at.desc())
        .limit(200)
        .all()
    )

    return render_template(
        'admin/background_task_logs.html',
        task=task,
        logs=logs,
    )


@admin_bp.route('/tasks/<int:task_id>/logs/data', methods=['GET'])
def fetch_task_logs(task_id: int):
    """Trả về log dạng JSON để auto-refresh giao diện."""

    task = BackgroundTask.query.get_or_404(task_id)
    logs = (
        BackgroundTaskLog.query.filter_by(task_id=task_id)
        .order_by(BackgroundTaskLog.created_at.desc())
        .limit(200)
        .all()
    )

    return success_response(data={
            'task': {
                'task_id': task.task_id,
                'task_name': task.task_name,
                'status': task.status,
                'progress': task.progress,
                'total': task.total,
                'message': task.message,
                'stop_requested': task.stop_requested,
                'last_updated': task.last_updated.isoformat() if task.last_updated else None,
            },
            'logs': [_serialize_task_log(log) for log in logs],
        }
    )

@admin_bp.route('/settings', methods=['GET'])
def manage_system_settings():
    """
    Mô tả: Quản lý các cài đặt hệ thống (ví dụ: chế độ bảo trì).
    """
    maintenance_mode = AppSettings.get('MAINTENANCE_MODE', False)
    maintenance_end_time = AppSettings.get('MAINTENANCE_END_TIME', '')
        
    telegram_token_setting = AppSettings.query.get('telegram_bot_token')

    raw_settings = AppSettings.query.order_by(AppSettings.key.asc()).all()
    
    # Filter out gamification/points settings - they're managed in Gamification section
    def _is_gamification_setting(key: str) -> bool:
        key_upper = key.upper()
        return (
            key_upper.startswith('FLASHCARD_') or
            key_upper.startswith('QUIZ_') or
            key_upper.startswith('COURSE_') or
            key_upper.startswith('VOCAB_') or
            key_upper.startswith('DAILY_LOGIN') or
            'SCORE' in key_upper or
            'BONUS' in key_upper or
            'POINTS' in key_upper
        )
    
    settings = [
        setting
        for setting in raw_settings
        if not _is_sensitive_setting(setting.key) 
           and setting.key not in CORE_SETTING_KEYS 
           and setting.key != 'telegram_bot_token'
           and not _is_gamification_setting(setting.key)
    ]
    data_type_options = ['string', 'int', 'bool', 'path', 'json']
    category_order = ['paths']

    users = User.query.order_by(User.username.asc()).all()
    quiz_sets = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    return render_template(
        'admin/system_settings.html',
        maintenance_mode=maintenance_mode,
        telegram_token_setting=telegram_token_setting,
        core_settings=_get_core_settings(),
        grouped_core_settings=_get_grouped_core_settings(),
        settings_by_category=_categorize_settings(settings),
        category_order=category_order,
        category_labels=SETTING_CATEGORY_LABELS,
        data_type_options=data_type_options,
        users=users,
        quiz_sets=quiz_sets,
        maintenance_end_time=maintenance_end_time
    )

@admin_bp.route('/settings', methods=['POST'])
def save_maintenance_mode():
    """Lưu chế độ bảo trì."""
    maintenance_mode = 'maintenance_mode' in request.form
    maintenance_end_time = request.form.get('maintenance_end_time', '')

    try:
        AppSettings.set('MAINTENANCE_MODE', maintenance_mode, category='system', description='Chế độ bảo trì')
        AppSettings.set('MAINTENANCE_END_TIME', maintenance_end_time, category='system', description='Thời gian kết thúc bảo trì')
        db.session.commit()
        
        _refresh_runtime_settings()
        flash('Cài đặt hệ thống đã được cập nhật thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')
        
    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/telegram-token', methods=['POST'])
def save_telegram_token():
    """Lưu Telegram Bot Token."""
    token_value = (request.form.get('value') or '').strip()
    
    setting = AppSettings.query.get('telegram_bot_token')
    old_value = setting.value if setting else None

    if setting:
        setting.value = token_value
        setting.data_type = 'string'
        flag_modified(setting, 'value')
    else:
        setting = AppSettings(
            key='telegram_bot_token',
            value=token_value,
            category='telegram',
            data_type='string',
            description='Telegram Bot API Token để gửi tin nhắn nhắc nhở.'
        )
        db.session.add(setting)
    
    db.session.commit()
    _log_setting_change(
        "update", key="telegram_bot_token", old_value=old_value, new_value=token_value
    )
    _refresh_runtime_settings()
    flash('Telegram Bot Token đã được lưu thành công!', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/core', methods=['POST'])
def update_core_settings():
    """Cập nhật nhanh các cấu hình vận hành quan trọng."""

    updated_count = 0
    pending_logs: list[tuple[str, object, object]] = []

    for field in CORE_SETTING_FIELDS:
        key = field["key"]
        data_type = str(field.get("data_type", "string")).lower()
        description = field.get("description")
        raw_value = request.form.get(key)

        if raw_value is None:
            current_app.logger.debug("Bỏ qua %s vì không có dữ liệu từ form", key)
            continue

        try:
            parsed_value = _parse_setting_value(raw_value, data_type, key=key)
            _validate_setting_value(parsed_value, data_type, key=key)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        setting = AppSettings.query.get(key)
        old_value = setting.value if setting else None

        if setting:
            setting.value = parsed_value
            setting.data_type = data_type
            setting.description = description
            flag_modified(setting, 'value')
        else:
            setting = AppSettings(
                key=key,
                value=parsed_value,
                category='system',
                data_type=data_type,
                description=description,
            )
            db.session.add(setting)

        pending_logs.append((key, old_value, parsed_value))
        updated_count += 1

    if updated_count:
        db.session.commit()
        for key, old_value, parsed_value in pending_logs:
            _log_setting_change("update", key=key, old_value=old_value, new_value=parsed_value)
        _refresh_runtime_settings()
        flash('Đã lưu cấu hình vận hành.', 'success')
    else:
        flash('Không có thay đổi nào được ghi nhận.', 'info')

    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/create', methods=['POST'])
def create_system_setting():
    """
    Mô tả: Thêm mới một cấu hình hệ thống từ biểu mẫu admin.
    """

    key = (request.form.get('key') or '').strip().upper()
    value = request.form.get('value')
    data_type = (request.form.get('data_type') or 'string').lower()
    description = (request.form.get('description') or '').strip() or None

    if not key:
        flash('Khóa cấu hình không được bỏ trống.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    if _is_sensitive_setting(key):
        flash('Khóa cấu hình này được bảo vệ và chỉ thiết lập qua biến môi trường.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    if AppSettings.query.get(key):
        flash('Khóa cấu hình đã tồn tại. Vui lòng chọn tên khác.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    try:
        parsed_value = _parse_setting_value(value, data_type, key=key)
        _validate_setting_value(parsed_value, data_type, key=key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting = AppSettings(key=key, value=parsed_value, category='system', data_type=data_type, description=description)
    db.session.add(setting)
    db.session.commit()

    _log_setting_change("create", key=key, old_value=None, new_value=parsed_value)
    _refresh_runtime_settings()
    flash('Đã thêm cấu hình mới thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/<string:setting_key>/update', methods=['POST'])
def update_system_setting(setting_key):
    """
    Mô tả: Cập nhật giá trị cấu hình hiện có.
    """

    setting = AppSettings.query.get_or_404(setting_key)

    if _is_sensitive_setting(setting.key):
        flash('Khóa cấu hình này được bảo vệ và không thể chỉnh sửa từ giao diện.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    data_type = (request.form.get('data_type') or setting.data_type or 'string').lower()
    description = (request.form.get('description') or '').strip() or None
    raw_value = request.form.get('value')

    try:
        parsed_value = _parse_setting_value(raw_value, data_type, key=setting.key)
        _validate_setting_value(parsed_value, data_type, key=setting.key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting.data_type = data_type
    setting.description = description
    old_value = setting.value
    setting.value = parsed_value
    flag_modified(setting, 'value')

    db.session.commit()
    _log_setting_change(
        "update", key=setting.key, old_value=old_value, new_value=parsed_value
    )
    _refresh_runtime_settings()
    flash('Đã cập nhật cấu hình thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/<string:setting_key>/delete', methods=['POST'])
def delete_system_setting(setting_key):
    """
    Mô tả: Xóa một cấu hình khỏi hệ thống.
    """

    setting = AppSettings.query.get_or_404(setting_key)

    if _is_sensitive_setting(setting.key):
        flash('Không thể xóa khóa cấu hình được bảo vệ.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    old_value = setting.value
    db.session.delete(setting)
    db.session.commit()

    current_app.config.pop(setting.key, None)
    _log_setting_change("delete", key=setting.key, old_value=old_value, new_value=None)
    _refresh_runtime_settings()

    flash('Đã xóa cấu hình.', 'info')
    return redirect(url_for('admin.manage_system_settings'))


@admin_bp.route('/settings/reset-progress', methods=['POST'])
def reset_learning_progress():
    """
    Đặt lại tiến độ học tập cho một người dùng hoặc toàn bộ người dùng của một bộ câu hỏi.
    """

    reset_scope = (request.form.get('reset_scope') or '').strip()
    confirmation = (request.form.get('confirmation') or '').strip()

    if reset_scope == 'user':
        user_id_raw = request.form.get('user_id')
        if not user_id_raw:
            flash('Vui lòng chọn người dùng cần đặt lại tiến độ.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            flash('ID người dùng không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        user = User.query.get(user_id)
        if not user:
            flash('Không tìm thấy người dùng được chọn.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET USER {user.username}"
        if confirmation != expected_confirmation:
            flash(
                f"Bạn cần nhập chính xác chuỗi xác nhận: '{expected_confirmation}'.",
                'warning',
            )
            return redirect(url_for('admin.manage_system_settings'))

        deleted_states = (
            UserContainerState.query.filter_by(user_id=user.user_id)
            .delete(synchronize_session=False)
        )
        deleted_progress = (
            LearningProgress.query.filter_by(user_id=user.user_id)
            .delete(synchronize_session=False)
        )
        deleted_notes = (
            UserNote.query.filter_by(user_id=user.user_id)
            .delete(synchronize_session=False)
        )
        deleted_feedback = (
            UserFeedback.query.filter_by(user_id=user.user_id)
            .delete(synchronize_session=False)
        )
        deleted_scores = (
            ScoreLog.query.filter_by(user_id=user.user_id)
            .delete(synchronize_session=False)
        )

        user.total_score = 0
        db.session.commit()

        flash(
            (
                f"Đã đặt lại tiến độ của {user.username}. "
                f"Đã đặt lại tiến độ của {user.username}. "
                f"Xóa {deleted_progress} mục tiến độ (flashcard/quiz/course), "
                f"{deleted_states} trạng thái container, {deleted_notes} ghi chú, {deleted_feedback} phản hồi và {deleted_scores} log điểm."
            ),
            'success',
        )
        return redirect(url_for('admin.manage_system_settings'))

    if reset_scope == 'container':
        container_id_raw = request.form.get('container_id')
        if not container_id_raw:
            flash('Vui lòng chọn bộ câu hỏi cần đặt lại tiến độ.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            container_id = int(container_id_raw)
        except (TypeError, ValueError):
            flash('ID bộ câu hỏi không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        container = LearningContainer.query.get(container_id)
        if not container:
            flash('Không tìm thấy bộ câu hỏi được chọn.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET CONTAINER {container.container_id}"
        if confirmation != expected_confirmation:
            flash(
                f"Bạn cần nhập chính xác chuỗi xác nhận: '{expected_confirmation}'.",
                'warning',
            )
            return redirect(url_for('admin.manage_system_settings'))

        item_subquery = (
            db.session.query(LearningItem.item_id)
            .filter(LearningItem.container_id == container.container_id)
            .subquery()
        )

        deleted_progress = (
            LearningProgress.query.filter(LearningProgress.item_id.in_(item_subquery))
            .delete(synchronize_session=False)
        )

        deleted_notes = (
            UserNote.query.filter(UserNote.item_id.in_(item_subquery))
            .delete(synchronize_session=False)
        )
        deleted_feedback = (
            UserFeedback.query.filter(UserFeedback.item_id.in_(item_subquery))
            .delete(synchronize_session=False)
        )
        deleted_scores = (
            ScoreLog.query.filter(ScoreLog.item_id.in_(item_subquery))
            .delete(synchronize_session=False)
        )
        deleted_states = (
            UserContainerState.query.filter_by(container_id=container.container_id)
            .delete(synchronize_session=False)
        )

        db.session.commit()

        flash(
            (
                f"Đã đặt lại tiến độ cho bộ câu hỏi '{container.title}'. "
                f"Đã đặt lại tiến độ cho bộ câu hỏi '{container.title}'. "
                f"Xóa {deleted_progress} mục tiến độ (flashcard/quiz/course), "
                f"{deleted_states} trạng thái container, {deleted_notes} ghi chú, {deleted_feedback} phản hồi và {deleted_scores} log điểm."
            ),
            'success',
        )
        return redirect(url_for('admin.manage_system_settings'))

    flash('Phạm vi đặt lại không hợp lệ.', 'danger')
    return redirect(url_for('admin.manage_system_settings'))
    
@admin_bp.route('/backup-restore')
def manage_backup_restore():
    """
    Mô tả: Hiển thị trang quản lý sao lưu và khôi phục dữ liệu.
    """
    # Lấy danh sách các file sao lưu hiện có
    backup_folder = _get_backup_folder()
    backup_entries: list[dict[str, object]] = []
    for filename in os.listdir(backup_folder):
        if not filename.endswith('.zip'):
            continue

        file_path = os.path.join(backup_folder, filename)
        created_at = datetime.fromtimestamp(os.path.getmtime(file_path))
        has_uploads = False

        try:
            # Kiểm tra file zip xem có thư mục uploads không
            with zipfile.ZipFile(file_path, 'r') as zipf:
                members = zipf.namelist()
                has_uploads = any(member.startswith('uploads/') for member in members)

                # Kiểm tra manifest (cho các bản sao lưu toàn bộ mới)
                if not has_uploads and 'manifest.json' in members:
                    try:
                        manifest_raw = zipf.read('manifest.json')
                        manifest_data = json.loads(manifest_raw.decode('utf-8'))
                        has_uploads = bool(manifest_data.get('includes_uploads', False))
                    except (KeyError, ValueError, UnicodeDecodeError) as exc:
                        current_app.logger.warning(
                            'Không thể đọc manifest của bản sao lưu %s: %s', filename, exc
                        )
        except zipfile.BadZipFile as exc:
            current_app.logger.warning('Không thể đọc nội dung bản sao lưu %s: %s', filename, exc)

        backup_entries.append(
            {
                'name': filename,
                'created_at': created_at,
                'created_at_label': created_at.strftime('%d/%m/%Y %H:%M:%S'),
                'has_uploads': has_uploads,
            }
        )

    # Sắp xếp theo ngày tạo mới nhất
    backup_entries.sort(key=lambda entry: entry['created_at'], reverse=True)

    # Lấy các tùy chọn dataset
    dataset_options = [
        {
            'key': key,
            'label': config['label'],
            'description': config['description'],
        }
        for key, config in DATASET_CATALOG.items()
    ]

    return render_template(
        'admin/backup_restore.html',
        backup_entries=backup_entries,
        dataset_options=dataset_options,
    )

@admin_bp.route('/backup/database', methods=['POST'])
def create_database_backup():
    """
    Mô tả: Tạo bản sao lưu cơ sở dữ liệu và lưu trên máy chủ.
    """
    try:
        backup_folder = _get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_database_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_folder, backup_filename)

        db_path = _resolve_database_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError('Không tìm thấy file cơ sở dữ liệu để sao lưu.')

        # Nén file database
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(db_path, os.path.basename(db_path))
            # Ghi file manifest
            manifest = {
                'type': 'database',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'database_file': os.path.basename(db_path),
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        flash('Đã sao lưu cơ sở dữ liệu thành công!', 'success')
    except Exception as exc:
        current_app.logger.error('Lỗi khi tạo bản sao lưu database: %s', exc)
        flash(f'Lỗi khi tạo bản sao lưu cơ sở dữ liệu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/backup/files/<path:filename>')
def download_backup_file(filename):
    """
    Mô tả: Cho phép tải xuống một file sao lưu.
    """
    backup_folder = _get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    return send_file(target_path, as_attachment=True, download_name=os.path.basename(target_path))


def _build_dataset_export_response(dataset_key):
    """
    Mô tả: Xử lý logic xuất một dataset (gói dữ liệu) cụ thể.
    """
    if dataset_key not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    config = DATASET_CATALOG[dataset_key]

    try:
        # Thu thập dữ liệu
        payload = _collect_dataset_payload(dataset_key)
        backup_folder = _get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mindstack_{dataset_key}_dataset_{timestamp}.zip'
        file_path = os.path.join(backup_folder, filename)

        # Ghi ra file zip
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            _write_dataset_to_zip(zipf, dataset_key, payload)

        flash(
            f"Đã xuất dữ liệu '{config['label']}' và lưu thành công dưới tên file {filename}.",
            'success',
        )
    except Exception as exc:
        current_app.logger.error('Lỗi khi xuất dataset %s: %s', dataset_key, exc)
        flash(f'Lỗi khi xuất dữ liệu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/backup/export', methods=['POST'])
def export_dataset_from_form():
    """
    Mô tả: Route xử lý khi người dùng bấm nút "Xuất dữ liệu" từ form.
    """
    dataset_key = request.form.get('dataset_key', '')
    if not dataset_key:
        flash('Vui lòng chọn gói dữ liệu cần xuất.', 'warning')
        return redirect(url_for('admin.manage_backup_restore'))

    return _build_dataset_export_response(dataset_key)


@admin_bp.route('/backup/export/<string:dataset_key>')
def export_dataset(dataset_key):
    """
    Mô tả: Route xử lý khi người dùng bấm link xuất (nếu có).
    """
    return _build_dataset_export_response(dataset_key)


@admin_bp.route('/backup/delete/<path:filename>', methods=['POST'])
def delete_backup_file(filename):
    """
    Mô tả: Xóa một file sao lưu khỏi máy chủ.
    """
    backup_folder = _get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    try:
        os.remove(target_path)
        flash('Đã xóa bản sao lưu thành công.', 'success')
    except OSError as exc:
        current_app.logger.error('Lỗi khi xóa bản sao lưu %s: %s', filename, exc)
        flash(f'Lỗi khi xóa bản sao lưu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/backup/full', methods=['POST'])
def download_full_backup():
    """
    Mô tả: Tạo gói sao lưu toàn bộ (DB + Uploads) và trả về cho người dùng tải xuống.
    """
    try:
        db_path = _resolve_database_path()
        uploads_folder = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_full_backup_{timestamp}.zip'

        # Tạo file zip tạm
        temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_file.close()

        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Nén database
            if os.path.exists(db_path):
                zipf.write(db_path, os.path.basename(db_path))

            # Nén thư mục uploads (nếu có)
            if uploads_folder and os.path.exists(uploads_folder):
                base_dir = os.path.dirname(uploads_folder)
                for foldername, _, filenames in os.walk(uploads_folder):
                    for fname in filenames:
                        file_path = os.path.join(foldername, fname)
                        # Giữ nguyên cấu trúc thư mục (vd: uploads/images/...)
                        arcname = os.path.relpath(file_path, base_dir)
                        zipf.write(file_path, arcname)

            # Ghi manifest
            manifest = {
                'type': 'full',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'includes_uploads': bool(uploads_folder and os.path.exists(uploads_folder)),
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        # Gửi file cho người dùng
        response = send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=backup_filename,
        )

        # Đăng ký hàm dọn dẹp file tạm sau khi request hoàn tất
        @after_this_request
        def _cleanup_temp_file(response):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass # Bỏ qua nếu không xóa được
            return response

        response.headers['X-Mindstack-Backup'] = 'full'
        return response
    except Exception as exc:
        current_app.logger.error('Lỗi khi tạo bản sao lưu toàn bộ: %s', exc)
        flash(f'Lỗi khi tạo bản sao lưu toàn bộ: {exc}', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/restore-dataset/<string:dataset_key>', methods=['POST'])
@admin_bp.route('/restore-dataset', methods=['POST'])
def restore_dataset(dataset_key = None):
    """
    Mô tả: Khôi phục dữ liệu từ file (zip/json) do người dùng tải lên.
    """
    dataset_hint = dataset_key or request.form.get('dataset_key') or None

    if dataset_hint and dataset_hint not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    upload = request.files.get('dataset_file')
    if not upload or upload.filename == '':
        flash('Vui lòng chọn file dữ liệu để khôi phục.', 'warning')
        return redirect(url_for('admin.manage_backup_restore'))

    try:
        # Gọi hàm xử lý chính
        result_kind, result_dataset_key = _restore_from_uploaded_bytes(upload.read(), dataset_hint)

        # Thông báo thành công
        if result_kind == 'dataset' and result_dataset_key:
            config = DATASET_CATALOG.get(result_dataset_key, {})
            label = config.get('label', result_dataset_key)
            flash(f"Đã khôi phục dữ liệu '{label}' từ file tải lên thành công!", 'success')
        elif result_kind == 'full':
            flash('Đã khôi phục toàn bộ dữ liệu từ gói sao lưu đã tải lên.', 'success')
        elif result_kind == 'database':
            flash('Đã khôi phục cơ sở dữ liệu từ gói sao lưu đã tải lên.', 'success')
        else:
            flash('Đã xử lý gói sao lưu thành công.', 'success')
    except Exception as exc:
        current_app.logger.error('Lỗi khi khôi phục dữ liệu từ file tải lên: %s', exc)
        flash(f'Lỗi khi khôi phục dữ liệu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))

@admin_bp.route('/restore/<string:filename>', methods=['POST'])
@admin_bp.route('/restore', methods=['POST'])
def restore_backup(filename = None):
    """
    Mô tả: Khôi phục dữ liệu từ một bản sao lưu đã chọn (lưu trên server).
    """
    try:
        if not filename:
            filename = request.form.get('filename', '')

        backup_folder = _get_backup_folder()
        backup_path = safe_join(backup_folder, filename)

        if not backup_path or not os.path.exists(backup_path):
            flash('File sao lưu không tồn tại.', 'danger')
            return redirect(url_for('admin.manage_backup_restore'))

        # Lấy tùy chọn từ form (nếu có)
        restore_database = request.form.get('restore_database', 'on') == 'on'
        restore_uploads = request.form.get('restore_uploads', 'on') == 'on'

        with zipfile.ZipFile(backup_path, 'r') as zipf:
            manifest_data, _ = _read_backup_manifest(zipf)
            manifest_type = manifest_data.get('type') if isinstance(manifest_data, dict) else None

            # Trường hợp 1: Khôi phục 1 phần (dataset)
            if manifest_type == 'dataset':
                dataset_key = None
                manifest_dataset = manifest_data.get('dataset') if isinstance(manifest_data, dict) else None
                if isinstance(manifest_dataset, str) and manifest_dataset in DATASET_CATALOG:
                    dataset_key = manifest_dataset
                else:
                    dataset_key = _infer_dataset_key_from_zip(zipf)

                if not dataset_key:
                    raise RuntimeError('Không thể xác định gói dữ liệu trong bản sao lưu.')

                payload = _extract_dataset_payload_from_zip(zipf, dataset_key)
                if not payload:
                    raise RuntimeError('Không tìm thấy dữ liệu hợp lệ trong gói sao lưu.')

                _apply_dataset_restore(dataset_key, payload)

                config = DATASET_CATALOG.get(dataset_key, {})
                label = config.get('label', dataset_key)
                flash(f"Đã khôi phục gói dữ liệu '{label}' thành công!", 'success')
                return redirect(url_for('admin.manage_backup_restore'))

            # Trường hợp 2: Khôi phục toàn bộ (full) hoặc chỉ DB (database)
            try:
                _restore_backup_from_zip(zipf, restore_database=restore_database, restore_uploads=restore_uploads)
            except RuntimeError as exc:
                # Xử lý trường hợp file zip cũ (không có manifest)
                message = str(exc)
                if 'không chứa file cơ sở dữ liệu hợp lệ' in message.lower():
                    dataset_key = _infer_dataset_key_from_zip(zipf)
                    if dataset_key:
                        payload = _extract_dataset_payload_from_zip(zipf, dataset_key)
                        if payload:
                            _apply_dataset_restore(dataset_key, payload)
                            config = DATASET_CATALOG.get(dataset_key, {})
                            label = config.get('label', dataset_key)
                            flash(f"Đã khôi phục gói dữ liệu '{label}' thành công!", 'success')
                            return redirect(url_for('admin.manage_backup_restore'))
                raise # Ném lại lỗi nếu không xử lý được

        flash('Đã khôi phục dữ liệu thành công!', 'success')
    except Exception as e:
        current_app.logger.error(f"Lỗi khi khôi phục dữ liệu: {e}")
        flash(f'Lỗi khi khôi phục dữ liệu: {e}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/settings/fetch-gemini-models', methods=['GET'])
def fetch_gemini_models_api():
    """
    API nội bộ để lấy danh sách model mới nhất từ Google.
    """
    result = GeminiClient.get_available_models()
    return jsonify(result)

@admin_bp.route('/settings/fetch-hf-models', methods=['GET'])
def fetch_hf_models_api():
    """
    API nội bộ để lấy danh sách model mới nhất từ Hugging Face.
    """
    result = HuggingFaceClient.get_available_models()
    return jsonify(result)


@admin_bp.route('/settings/browse-directories', methods=['GET'])
def browse_directories_api():
    """
    API nội bộ để duyệt thư mục trên server cho chức năng chọn đường dẫn.
    Trả về danh sách thư mục con của đường dẫn được chỉ định.
    """
    base_path = request.args.get('path', '')
    
    # Nếu không có path, bắt đầu từ thư mục gốc của project
    if not base_path:
        base_path = current_app.root_path
    
    # Đảm bảo path tồn tại và là thư mục
    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        return error_response('Đường dẫn không tồn tại hoặc không phải thư mục.', 'BAD_REQUEST', 400, details={'directories': [], 'current_path': base_path})
    
    try:
        directories = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                # Bỏ qua thư mục ẩn và một số thư mục hệ thống
                if item.startswith('.') or item in ('__pycache__', 'node_modules', '.git', 'venv', '.venv'):
                    continue
                directories.append({
                    'name': item,
                    'path': item_path.replace('\\', '/'),
                })
        
        # Sắp xếp theo tên
        directories.sort(key=lambda x: x['name'].lower())
        
        # Lấy parent path
        parent_path = os.path.dirname(base_path)
        if parent_path == base_path:
            parent_path = None
        
        return success_response(data={
            'directories': directories,
            'current_path': base_path.replace('\\', '/'),
            'parent_path': parent_path.replace('\\', '/') if parent_path else None,
        })
    except PermissionError:
        return error_response('Không có quyền truy cập thư mục này.', 'FORBIDDEN', 403, details={'directories': [], 'current_path': base_path})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi duyệt thư mục: {e}")
        return error_response(f'Lỗi: {str(e)}', 'SERVER_ERROR', 500, details={'directories': [], 'current_path': base_path})


@admin_bp.route('/settings/create-directory', methods=['POST'])
def create_directory_api():
    """
    API nội bộ để tạo thư mục mới trong folder picker.
    """
    data = request.get_json(silent=True) or {}
    parent_path = data.get('parent_path', '')
    folder_name = (data.get('folder_name') or '').strip()
    
    if not folder_name:
        return error_response('Tên thư mục không được để trống.', 'BAD_REQUEST', 400)
    
    # Loại bỏ ký tự không hợp lệ
    import re
    folder_name = re.sub(r'[<>:"/\\|?*]', '', folder_name)
    if not folder_name:
        return error_response('Tên thư mục chứa ký tự không hợp lệ.', 'BAD_REQUEST', 400)
    
    if not parent_path:
        parent_path = current_app.root_path
    
    if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
        return error_response('Thư mục cha không tồn tại.', 'BAD_REQUEST', 400)
    
    new_path = os.path.join(parent_path, folder_name)
    
    if os.path.exists(new_path):
        return error_response('Thư mục đã tồn tại.', 'CONFLICT', 409)
    
    try:
        os.makedirs(new_path, exist_ok=True)
        return success_response(message=f'Đã tạo thư mục "{folder_name}".', data={'new_path': new_path.replace('\\', '/')})
    except PermissionError:
        return error_response('Không có quyền tạo thư mục.', 'FORBIDDEN', 403)
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tạo thư mục: {e}")
        return error_response(f'Lỗi: {str(e)}', 'SERVER_ERROR', 500)


# ==================== TEMPLATE MANAGEMENT ====================

@admin_bp.route('/templates')
@login_required
def manage_templates():
    """
    Trang quản lý giao diện template.
    Admin có thể chọn version cho từng loại template.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        abort(403)
    
    from ...services.template_service import TemplateService
    
    # Get all template settings
    template_settings = TemplateService.get_all_template_settings()
    
    return render_template(
        'admin/manage_templates.html',
        template_settings=template_settings,
    )


@admin_bp.route('/templates/update', methods=['POST'])
@login_required
def update_template_settings():
    """
    API endpoint để lưu cài đặt template.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        return error_response('Không có quyền.', 'FORBIDDEN', 403)
    
    from ...services.template_service import TemplateService
    from ...models import db
    
    try:
        data = request.get_json() or {}
        updates = data.get('updates', {})
        
        if not updates:
            return error_response('Không có thay đổi.', 'BAD_REQUEST', 400)
        
        for template_type, version in updates.items():
            if template_type and version:
                TemplateService.set_active_template(
                    template_type,
                    version,
                    user_id=current_user.user_id
                )
                current_app.logger.info(
                    f"Template updated by {current_user.username}: {template_type} -> {version}"
                )
        
        return success_response(message='Đã cập nhật cài đặt giao diện.')
    
    except Exception as e:
        current_app.logger.error(f"Error updating template settings: {e}")
        return error_response(f'Lỗi: {str(e)}', 'SERVER_ERROR', 500)


# =====================================================================
# SRS / Memory Power Configuration Routes
# =====================================================================

@admin_bp.route('/fsrs-config', methods=['GET'])
@login_required
def fsrs_config():
    """
    Trang cấu hình FSRS v5 (Free Spaced Repetition Scheduler).
    Thay thế hoàn toàn cấu hình SM-2 cũ.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        abort(403)

    from ...services.memory_power_config_service import MemoryPowerConfigService
    
    # Get current values for FSRS keys
    keys = [
        'FSRS_DESIRED_RETENTION', 
        'FSRS_MAX_INTERVAL', 
        'FSRS_ENABLE_FUZZ', 
        'FSRS_GLOBAL_WEIGHTS'
    ]
    
    settings = {}
    for key in keys:
        # Get raw value
        val = MemoryPowerConfigService.get(key)
        # Type safety
        if key == 'FSRS_GLOBAL_WEIGHTS' and not isinstance(val, list):
             val = [] 
        settings[key] = val

    from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
    return render_template(
        'admin/fsrs_config.html',
        settings=settings,
        defaults=DEFAULT_APP_CONFIGS
    )


@admin_bp.route('/fsrs-config', methods=['POST'])
@login_required
def save_fsrs_config():
    """
    API lưu cấu hình FSRS v5.
    Chỉ chấp nhận các tham số chuẩn của FSRS.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        return error_response('Không có quyền.', 'FORBIDDEN', 403)

    from ...services.memory_power_config_service import MemoryPowerConfigService

    try:
        data = request.get_json() or {}
        
        # Valid keys for FSRS v5
        allowed_keys = {
            'FSRS_DESIRED_RETENTION': float,
            'FSRS_MAX_INTERVAL': int,
            'FSRS_ENABLE_FUZZ': bool,
            'FSRS_GLOBAL_WEIGHTS': list
        }
        
        parsed_settings = {}
        
        for key, expected_type in allowed_keys.items():
            if key in data:
                val = data[key]
                # Type enforcement
                if expected_type == float:
                    val = float(val)
                elif expected_type == int:
                    val = int(val)
                elif expected_type == bool:
                    val = bool(val)
                elif expected_type == list:
                    if not isinstance(val, list):
                        raise ValueError(f"{key} phải là danh sách.")
                    if key == 'FSRS_GLOBAL_WEIGHTS' and len(val) != 19:
                         current_app.logger.warning(f"FSRS_GLOBAL_WEIGHTS length is {len(val)}, expected 19.")
                
                parsed_settings[key] = val

        if not parsed_settings:
            return error_response('Không có dữ liệu hợp lệ để lưu.', 'BAD_REQUEST', 400)

        # Update via Service
        MemoryPowerConfigService.save_all(parsed_settings, user_id=current_user.user_id)

        current_app.logger.info(
            f"FSRS config updated by {current_user.username}: {list(parsed_settings.keys())}"
        )
        
        return success_response(message='Cấu hình FSRS đã được lưu thành công.')
        
    except ValueError as e:
        return error_response(f'Lỗi dữ liệu: {str(e)}', 'BAD_REQUEST', 400)
    except Exception as e:
        current_app.logger.error(f"Error saving FSRS config: {e}")
        return error_response(f'Lỗi hệ thống: {str(e)}', 'SERVER_ERROR', 500)





# === Quiz Config Routes ===

@admin_bp.route('/content-config', methods=['GET'])
@login_required
def content_config_page():
    """Admin page for managing both Quiz and Flashcard configurations."""
    if current_user.user_role != 'admin':
        abort(403)
        
    quiz_settings = QuizConfigService.get_grouped()
    flashcard_settings = FlashcardConfigService.get_grouped()
    
    return render_template('admin/content_config.html', 
                          quiz_settings=quiz_settings,
                          flashcard_settings=flashcard_settings)

@admin_bp.route('/quiz-config', methods=['GET'])
@login_required
def quiz_config_page():
    """[DEPRECATED] Redirects to combined content config."""
    return redirect(url_for('admin.content_config_page'))



@admin_bp.route('/quiz-config/save', methods=['POST'])
@login_required
def save_quiz_config():
    """API to save updated quiz configuration."""
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    try:
        data = request.json or {}
        settings = data.get('settings', {})
        
        QuizConfigService.save_all(settings, user_id=current_user.user_id)
        
        current_app.logger.info(
            f"Quiz config updated by {current_user.username}"
        )
        
        return jsonify({'success': True, 'message': 'Cấu hình Quiz đã được lưu thành công!'})
    except Exception as e:
        current_app.logger.error(f"Failed to save quiz config: {e}")
        return jsonify({'success': False, 'message': f'Lỗi khi lưu: {str(e)}'}), 500


@admin_bp.route('/quiz-config/reset', methods=['POST'])
@login_required
def reset_quiz_config():
    """API to reset quiz configuration to defaults."""
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403
        
    try:
        QuizConfigService.reset_to_defaults(user_id=current_user.user_id)
        return jsonify({'success': True, 'message': 'Đã khôi phục cài đặt gốc!'})
    except Exception as e:
        current_app.logger.error(f"Failed to reset quiz config: {e}")
        return jsonify({'success': False, 'message': f'Lỗi khi reset: {str(e)}'}), 500
# ==========================================
# [NEW] Flashcard Configuration Routes
# ==========================================

@admin_bp.route('/flashcard-config', methods=['GET'])
@login_required
def flashcard_config():
    """[DEPRECATED] Redirects to combined content config."""
    return redirect(url_for('admin.content_config_page'))



@admin_bp.route('/flashcard-config/save', methods=['POST'])
@login_required
def save_flashcard_config():
    """API lưu cấu hình Flashcard."""
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        FlashcardConfigService.save_all(settings, user_id=current_user.id)
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình Flashcard thành công.'})
    except Exception as e:
        current_app.logger.error(f"Error saving flashcard config: {e}")
        return jsonify({'success': False, 'message': f'Lỗi khi lưu cấu hình: {str(e)}'}), 500


@admin_bp.route('/flashcard-config/reset', methods=['POST'])
@login_required
def reset_flashcard_config():
    """API reset cấu hình Flashcard về mặc định."""
    try:
        FlashcardConfigService.reset_to_defaults(user_id=current_user.id)
        return jsonify({'success': True, 'message': 'Đã khôi phục cấu hình Flashcard về mặc định.'})
    except Exception as e:
        current_app.logger.error(f"Error resetting flashcard config: {e}")
        return jsonify({'success': False, 'message': f'Lỗi khi reset cấu hình: {str(e)}'}), 500

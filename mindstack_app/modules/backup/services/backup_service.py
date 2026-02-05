# File: mindstack_app/modules/backup/services/backup_service.py
import os
import io
import csv
import json
import shutil
import zipfile
import tempfile
from collections import OrderedDict
from datetime import datetime, date, time
from typing import Optional, Dict

from flask import current_app
from sqlalchemy.sql.sqltypes import DateTime, Date, Time

from mindstack_app.models import (
    db, User, LearningContainer, LearningGroup, LearningItem, ContainerContributor,
    ApiKey, BackgroundTask, BackgroundTaskLog, AppSettings,
    UserContainerState, ScoreLog,
    Goal, UserGoal, GoalProgress, Note,
    Feedback, FeedbackAttachment,
    LearningSession, UserItemMarker, Badge, UserBadge,
    QuizBattleRoom, QuizBattleParticipant, QuizBattleRound, QuizBattleAnswer, QuizBattleMessage,
    FlashcardCollabRoom, FlashcardCollabParticipant, FlashcardCollabRound, FlashcardCollabAnswer, FlashcardCollabMessage, FlashcardRoomProgress,
    AiTokenLog, AiCache,
    Notification, PushSubscription, NotificationPreference,
    UserMetric, DailyStat, Achievement, TranslationHistory, Streak
)
from mindstack_app.modules.learning_history.models import StudyLog
from mindstack_app.modules.fsrs.interface import FSRSInterface
# FSRS Model entity retrieved via Interface for DATASET_CATALOG mapping
ItemMemoryStateModel = FSRSInterface.get_all_memory_states_query().column_descriptions[0]['entity']
from mindstack_app.core.config import Config
from mindstack_app.services.config_service import get_runtime_config

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
                ItemMemoryStateModel,
                ScoreLog,
                UserGoal,
                GoalProgress,
                Note,
                LearningSession,
                StudyLog,
                UserItemMarker,
                UserBadge,
                Badge,
            ],
        },
        'goals_notes': {
            'label': 'Mục tiêu & ghi chú học tập',
            'description': 'Chỉ bao gồm dữ liệu mục tiêu học tập và ghi chú cá nhân của người học.',
            'models': [Goal, UserGoal, Note],
        },
        'system_configs': {
            'label': 'Cấu hình hệ thống & API',
            'description': 'Các thiết lập hệ thống, tác vụ nền và khóa API tích hợp.',
            'models': [AppSettings, BackgroundTask, BackgroundTaskLog, ApiKey],
        },
        'feedback_reports': {
            'label': 'Phản hồi & báo cáo từ người dùng',
            'description': 'Tập trung vào phản hồi của người dùng.',
            'models': [Feedback, FeedbackAttachment],
        },
        'ai_data': {
            'label': 'Dữ liệu AI (Logs & Cache)',
            'description': 'Lịch sử token sử dụng và cache phản hồi của AI.',
            'models': [AiTokenLog, AiCache],
        },
        'notifications': {
            'label': 'Thông báo & Đăng ký Push',
            'description': 'Lịch sử thông báo, cài đặt đăng ký và tùy chọn thông báo của người dùng.',
            'models': [Notification, PushSubscription, NotificationPreference],
        },
        'stats_analytics': {
            'label': 'Thống kê & Phân tích',
            'description': 'Số liệu người dùng, thống kê hàng ngày, thành tựu và lịch sử dịch.',
            'models': [UserMetric, DailyStat, Achievement, TranslationHistory],
        },
        'multiplayer': {
            'label': 'Multiplayer (Quiz & Flashcard)',
            'description': 'Dữ liệu các phòng chơi, người tham gia và tin nhắn chat.',
            'models': [
                QuizBattleRoom, QuizBattleParticipant, QuizBattleRound, QuizBattleAnswer, QuizBattleMessage,
                FlashcardCollabRoom, FlashcardCollabParticipant, FlashcardCollabRound, FlashcardCollabAnswer, FlashcardCollabMessage, FlashcardRoomProgress
            ],
        },
        'full_database_json': {
            'label': 'Toàn bộ cơ sở dữ liệu (JSON)',
            'description': 'Xuất tất cả dữ liệu trong hệ thống dưới dạng JSON (trừ file uploads).',
            'models': [
                User, LearningContainer, LearningGroup, LearningItem, ContainerContributor,
                UserContainerState, ItemMemoryStateModel, ScoreLog, UserGoal, GoalProgress, Note,
                LearningSession, StudyLog, UserItemMarker, Badge, UserBadge,
                Feedback, FeedbackAttachment,
                AppSettings, BackgroundTask, BackgroundTaskLog, ApiKey,
                QuizBattleRoom, QuizBattleParticipant, QuizBattleRound, QuizBattleRound, QuizBattleAnswer, QuizBattleMessage,
                FlashcardCollabRoom, FlashcardCollabParticipant, FlashcardCollabRound, FlashcardCollabAnswer, FlashcardCollabMessage, FlashcardRoomProgress,
                AiTokenLog, AiCache,
                Notification, PushSubscription, NotificationPreference,
                UserMetric, DailyStat, Achievement, TranslationHistory
            ],
        },
    }
)

def resolve_database_path():
    uri = get_runtime_config('SQLALCHEMY_DATABASE_URI', Config.SQLALCHEMY_DATABASE_URI)
    if not uri:
        raise RuntimeError('Hệ thống chưa cấu hình kết nối cơ sở dữ liệu.')
    if uri.startswith('sqlite:///'):
        return uri.replace('sqlite:///', '')
    raise RuntimeError('Chức năng sao lưu hiện chỉ hỗ trợ cơ sở dữ liệu SQLite.')

def get_backup_folder():
    backup_folder = Config.BACKUP_FOLDER
    if not backup_folder:
        current_app.logger.error("LỖI CẤU HÌNH: BACKUP_FOLDER không được định nghĩa trong config.py.")
        raise RuntimeError("Lỗi cấu hình: BACKUP_FOLDER chưa được thiết lập.")
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder

def serialize_instance(instance):
    data: dict[str, object] = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif isinstance(value, date):
            data[column.name] = value.isoformat()
        elif isinstance(value, time):
            data[column.name] = value.isoformat()
        else:
            data[column.name] = value
    return data

def coerce_column_value(column, value):
    if value is None:
        return None
    column_type = column.type
    try:
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
        return value
    return value

def collect_dataset_payload(dataset_key):
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')
    payload: dict[str, list[dict[str, object]]] = {}
    for model in config['models']:
        rows = model.query.order_by(*model.__table__.primary_key.columns).all()
        payload[model.__tablename__] = [serialize_instance(row) for row in rows]
    return payload

def write_dataset_to_zip(zipf, dataset_key, payload):
    manifest = {
        'type': 'dataset',
        'dataset': dataset_key,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'tables': list(payload.keys()),
    }
    zipf.writestr(f'{dataset_key}/manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    for table_name, records in payload.items():
        json_bytes = json.dumps(records, ensure_ascii=False, indent=2).encode('utf-8')
        zipf.writestr(f'{dataset_key}/{table_name}.json', json_bytes)
        if records:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
            zipf.writestr(f'{dataset_key}/{table_name}.csv', output.getvalue())

def read_backup_manifest(zipf):
    candidates = ['manifest.json']
    candidates.extend(name for name in zipf.namelist() if name.endswith('/manifest.json'))
    for candidate in candidates:
        try:
            raw = zipf.read(candidate)
        except KeyError:
            continue
        try:
            return json.loads(raw.decode('utf-8')), candidate
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return None, None

def extract_dataset_payload_from_zip(zipf, dataset_key):
    payload: dict[str, list[dict[str, object]]] = {}
    members = set(zipf.namelist())
    for model in DATASET_CATALOG[dataset_key]['models']:
        table_name = model.__tablename__
        for candidate in (f'{dataset_key}/{table_name}.json', f'{table_name}.json'):
            if candidate not in members:
                continue
            try:
                data = json.loads(zipf.read(candidate).decode('utf-8'))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(data, list):
                payload[table_name] = data
            break
    return payload

def infer_dataset_key_from_zip(zipf):
    members = set(zipf.namelist())
    best_match: tuple[Optional[str], int] = (None, 0)
    for dataset_key, config in DATASET_CATALOG.items():
        table_names = {model.__tablename__ for model in config['models']}
        available = {
            table_name
            for table_name in table_names
            if f'{dataset_key}/{table_name}.json' in members or f'{table_name}.json' in members
        }
        if not available:
            continue
        if not available.issubset(table_names):
            continue
        if best_match[0] is None or len(table_names) < best_match[1]:
            best_match = (dataset_key, len(table_names))
    return best_match[0]

def infer_dataset_key_from_json(data):
    available_tables = {key for key, value in data.items() if isinstance(value, list)}
    if not available_tables:
        return None
    best_match: tuple[Optional[str], int] = (None, 0)
    for dataset_key, config in DATASET_CATALOG.items():
        table_names = {model.__tablename__ for model in config['models']}
        if not available_tables.issubset(table_names):
            continue
        if best_match[0] is None or len(table_names) < best_match[1]:
            best_match = (dataset_key, len(table_names))
    return best_match[0]

def restore_backup_from_zip(zipf, restore_database=True, restore_uploads=True):
    members = zipf.namelist()
    db_path: Optional[str] = None
    if restore_database:
        db.session.close()
        db.engine.dispose()
        db_path = resolve_database_path()
    temp_dir = tempfile.mkdtemp(prefix='mindstack_restore_')
    try:
        if restore_database:
            if not db_path:
                raise RuntimeError('Không thể xác định đường dẫn cơ sở dữ liệu để khôi phục.')
            db_basename = os.path.basename(db_path)
            db_member = next((m for m in members if os.path.basename(m) == db_basename), None)
            if not db_member:
                raise RuntimeError('Gói sao lưu không chứa file cơ sở dữ liệu hợp lệ.')
            zipf.extract(db_member, temp_dir)
            extracted_db_path = os.path.join(temp_dir, db_member)
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            shutil.copy2(extracted_db_path, db_path)
        if restore_uploads:
            uploads_folder = Config.UPLOAD_FOLDER
            if uploads_folder and any(member.startswith('uploads/') for member in members):
                zipf.extractall(temp_dir)
                source_uploads = os.path.join(temp_dir, 'uploads')
                if os.path.exists(source_uploads):
                    shutil.rmtree(uploads_folder, ignore_errors=True)
                    shutil.copytree(source_uploads, uploads_folder, dirs_exist_ok=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def apply_dataset_restore(dataset_key, payload):
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')
    if db.session.is_active:
        db.session.rollback()
    with db.session.begin():
        for model in reversed(config['models']):
            db.session.execute(db.delete(model))
        for model in config['models']:
            records = payload.get(model.__tablename__, [])
            if not records:
                continue
            for record in records:
                instance = model()
                for column in model.__table__.columns:
                    if column.name not in record:
                        continue
                    setattr(instance, column.name, coerce_column_value(column, record[column.name]))
                db.session.add(instance)

def restore_from_uploaded_bytes(raw_bytes, dataset_hint=None) -> Dict[str, object]:
    if not raw_bytes:
        return {'success': False, 'error': 'File tải lên rỗng.'}
    buffer = io.BytesIO(raw_bytes)
    try:
        if zipfile.is_zipfile(buffer):
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as zipf:
                manifest_data, _ = read_backup_manifest(zipf)
                manifest_type = manifest_data.get('type') if isinstance(manifest_data, dict) else None
                if manifest_type == 'full':
                    includes_uploads = bool(manifest_data.get('includes_uploads', False))
                    restore_backup_from_zip(zipf, restore_database=True, restore_uploads=includes_uploads)
                    return {'success': True, 'message': 'Đã khôi phục toàn bộ hệ thống (Full Backup).'}
                if manifest_type == 'database':
                    restore_backup_from_zip(zipf, restore_database=True, restore_uploads=False)
                    return {'success': True, 'message': 'Đã khôi phục cơ sở dữ liệu.'}
                dataset_key = None
                if dataset_hint and dataset_hint in DATASET_CATALOG:
                    dataset_key = dataset_hint
                elif manifest_data and isinstance(manifest_data, dict):
                    manifest_dataset = manifest_data.get('dataset')
                    if isinstance(manifest_dataset, str) and manifest_dataset in DATASET_CATALOG:
                        dataset_key = manifest_dataset
                if not dataset_key:
                    dataset_key = infer_dataset_key_from_zip(zipf)
                if dataset_key:
                    payload = extract_dataset_payload_from_zip(zipf, dataset_key)
                    if not payload:
                        return {'success': False, 'error': 'Không tìm thấy dữ liệu hợp lệ trong gói sao lưu.'}
                    apply_dataset_restore(dataset_key, payload)
                    return {'success': True, 'message': f"Đã khôi phục dataset '{DATASET_CATALOG[dataset_key]['label']}'."}
            return {'success': False, 'error': 'Không thể xác định loại gói sao lưu từ file ZIP.'}
        
        try:
            text = raw_bytes.decode('utf-8')
        except UnicodeDecodeError as exc:
            return {'success': False, 'error': 'File tải lên không phải là file ZIP hoặc JSON hợp lệ.'}
        
        data = json.loads(text)
        if not isinstance(data, dict):
            return {'success': False, 'error': 'Định dạng JSON không hợp lệ.'}
        dataset_key = None
        if dataset_hint and dataset_hint in DATASET_CATALOG:
            dataset_key = dataset_hint
        else:
            dataset_key = infer_dataset_key_from_json(data)
        if not dataset_key:
            return {'success': False, 'error': 'Không thể xác định dataset phù hợp cho dữ liệu đã tải lên.'}
        payload = {table: records for table, records in data.items() if isinstance(records, list)}
        if not payload:
            return {'success': False, 'error': 'Không tìm thấy dữ liệu hợp lệ trong file JSON.'}
        apply_dataset_restore(dataset_key, payload)
        return {'success': True, 'message': f"Đã khôi phục dataset '{DATASET_CATALOG[dataset_key]['label']}' từ JSON."}
        
    except Exception as e:
        current_app.logger.error(f"Restore error: {e}")
        return {'success': False, 'error': str(e)}

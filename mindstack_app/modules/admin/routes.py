# File: Mindstack/web/mindstack_app/modules/admin/routes.py
# Version: 2.5
# Mục đích: Chứa các route và logic cho bảng điều khiển admin tổng quan.
# ĐÃ THÊM: Route và logic để quản lý việc sao lưu và khôi phục dữ liệu.

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
from flask_login import login_required, current_user
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
    SystemSetting,
    UserContainerState,
    FlashcardProgress,
    QuizProgress,
    CourseProgress,
    ScoreLog,
    LearningGoal,
    UserNote,
    UserFeedback,
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
from uuid import uuid4
from werkzeug.utils import secure_filename, safe_join
from collections import OrderedDict
from typing import Optional
from sqlalchemy.sql.sqltypes import DateTime, Date, Time
from datetime import date, time

from ..learning.flashcard_learning.audio_service import AudioService
from ..learning.flashcard_learning.image_service import ImageService

audio_service = AudioService()
image_service = ImageService()


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
                FlashcardProgress,
                QuizProgress,
                CourseProgress,
                ScoreLog,
                LearningGoal,
                UserNote,
                UserFeedback,
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
            'models': [SystemSetting, BackgroundTask, ApiKey],
        },
        'feedback_reports': {
            'label': 'Phản hồi & báo cáo từ người dùng',
            'description': 'Tập trung vào phản hồi, điểm số và lịch sử tương tác phục vụ phân tích.',
            'models': [UserFeedback, ScoreLog],
        },
    }
)


def _resolve_database_path() -> str:
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri:
        raise RuntimeError('Hệ thống chưa cấu hình kết nối cơ sở dữ liệu.')
    if uri.startswith('sqlite:///'):
        return uri.replace('sqlite:///', '')
    raise RuntimeError('Chức năng sao lưu hiện chỉ hỗ trợ cơ sở dữ liệu SQLite.')


def _get_backup_folder() -> str:
    backup_folder = os.path.join(current_app.root_path, 'backups')
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder


def _serialize_instance(instance) -> dict:
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


def _coerce_column_value(column, value):
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


def _collect_dataset_payload(dataset_key: str) -> dict[str, list[dict[str, object]]]:
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')

    payload: dict[str, list[dict[str, object]]] = {}
    for model in config['models']:
        rows = model.query.order_by(*model.__table__.primary_key.columns).all()
        payload[model.__tablename__] = [_serialize_instance(row) for row in rows]
    return payload


def _write_dataset_to_zip(zipf: zipfile.ZipFile, dataset_key: str, payload: dict[str, list[dict[str, object]]]) -> None:
    manifest = {
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


def _load_dataset_payload(file_storage, dataset_key: str) -> dict[str, list[dict[str, object]]]:
    raw_bytes = file_storage.read()
    if not raw_bytes:
        raise ValueError('File tải lên rỗng.')

    payload: dict[str, list[dict[str, object]]] = {}
    buffer = io.BytesIO(raw_bytes)

    if zipfile.is_zipfile(buffer):
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as zipf:
            members = set(zipf.namelist())
            for model in DATASET_CATALOG[dataset_key]['models']:
                table_name = model.__tablename__
                candidates = [
                    f'{dataset_key}/{table_name}.json',
                    f'{table_name}.json',
                ]
                json_member = next((candidate for candidate in candidates if candidate in members), None)
                if not json_member:
                    continue
                data = json.loads(zipf.read(json_member).decode('utf-8'))
                if isinstance(data, list):
                    payload[table_name] = data
        return payload

    buffer.seek(0)
    text = buffer.read().decode('utf-8')
    data = json.loads(text)
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if isinstance(v, list)}
    raise ValueError('Định dạng file không hợp lệ. Hãy tải lên file JSON hoặc ZIP hợp lệ.')


def _apply_dataset_restore(dataset_key: str, payload: dict[str, list[dict[str, object]]]) -> None:
    config = DATASET_CATALOG.get(dataset_key)
    if not config:
        raise KeyError('Dataset không tồn tại.')

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
                    setattr(instance, column.name, _coerce_column_value(column, record[column.name]))
                db.session.add(instance)

from . import admin_bp  # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.
from .context_processors import build_admin_sidebar_metrics

ADMIN_ALLOWED_MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.opus',
    '.mp4', '.webm', '.mov', '.mkv', '.avi', '.m4v',
    '.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.txt', '.zip', '.rar', '.7z', '.json'
}


def _format_file_size(num_bytes: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _normalize_subpath(path_value: str | None) -> str:
    normalized = os.path.normpath(path_value or '').replace('\\', '/')
    if normalized in ('', '.', '/'):  # Root folder
        return ''
    if normalized.startswith('..'):
        raise ValueError('Đường dẫn không hợp lệ.')
    return normalized.strip('/')


def _collect_directory_listing(base_dir: str, upload_root: str):
    directories = []
    files = []

    if not os.path.isdir(base_dir):
        return directories, files

    for entry in os.scandir(base_dir):
        if entry.name.startswith('.'):
            continue
        relative = os.path.relpath(entry.path, upload_root).replace('\\', '/')
        if entry.is_dir():
            directories.append({
                'name': entry.name,
                'path': relative.strip('/'),
                'item_count': sum(1 for _ in os.scandir(entry.path)) if os.path.isdir(entry.path) else 0,
                'modified': datetime.fromtimestamp(entry.stat().st_mtime)
            })
        elif entry.is_file():
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

    directories.sort(key=lambda item: item['name'].lower())
    files.sort(key=lambda item: item['modified'], reverse=True)
    return directories, files

# Middleware để kiểm tra quyền admin cho toàn bộ Blueprint admin
@admin_bp.before_request 
@login_required 
def admin_required():
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        flash('Bạn không có quyền truy cập khu vực quản trị.', 'danger')
        abort(403) 

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def admin_dashboard():
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

    recent_users = (
        User.query.filter(User.last_seen.isnot(None))
        .order_by(User.last_seen.desc())
        .limit(5)
        .all()
    )

    recent_containers = (
        LearningContainer.query.order_by(LearningContainer.created_at.desc())
        .limit(5)
        .all()
    )

    recent_tasks = (
        BackgroundTask.query.order_by(nullslast(BackgroundTask.last_updated.desc()))
        .limit(4)
        .all()
    )

    overview_metrics = build_admin_sidebar_metrics()

    return render_template(
        'dashboard.html',
        stats_data=stats_data,
        recent_users=recent_users,
        recent_containers=recent_containers,
        recent_tasks=recent_tasks,
        overview_metrics=overview_metrics,
    )


@admin_bp.route('/media-library', methods=['GET', 'POST'])
def media_library():
    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        current_folder = _normalize_subpath(
            request.form.get('current_folder') if request.method == 'POST' else request.args.get('folder')
        )
    except ValueError:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    target_dir = safe_join(upload_root, current_folder) if current_folder else upload_root
    if target_dir is None:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    os.makedirs(target_dir, exist_ok=True)

    if request.method == 'POST':
        action = request.form.get('action', 'upload')
        if action == 'create_folder':
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

                    candidate_name = filename
                    destination = os.path.join(target_dir, candidate_name)
                    while os.path.exists(destination):
                        name_part, extension_part = os.path.splitext(filename)
                        candidate_name = f"{name_part}_{uuid4().hex[:6]}{extension_part}"
                        destination = os.path.join(target_dir, candidate_name)

                    try:
                        file.save(destination)
                        saved.append(candidate_name)
                    except Exception as exc:  # pragma: no cover - lỗi IO hiếm gặp
                        current_app.logger.exception('Không thể lưu file %s: %s', candidate_name, exc)
                        skipped.append(original_name)

                if saved:
                    flash(f'Đã tải lên {len(saved)} file thành công.', 'success')
                if skipped:
                    flash('Một số file bị bỏ qua: ' + ', '.join(skipped), 'warning')

        return redirect(url_for('admin.media_library', folder=current_folder or None))

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
        'media_library.html',
        directories=directories,
        files=files,
        current_folder=current_folder,
        parent_folder=parent_folder,
        breadcrumb=breadcrumb,
        total_size=total_size,
    )


@admin_bp.route('/media-library/delete', methods=['POST'])
def delete_media_item():
    upload_root = current_app.config.get('UPLOAD_FOLDER')
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
    except Exception as exc:  # pragma: no cover - lỗi IO hiếm gặp
        current_app.logger.exception('Không thể xóa file %s: %s', full_path, exc)
        flash('Không thể xóa file. Vui lòng thử lại.', 'danger')

    parent_folder = '/'.join(relative_path.split('/')[:-1])
    return redirect(url_for('admin.media_library', folder=parent_folder or None))


@admin_bp.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền.
    """
    tasks = BackgroundTask.query.all()
    desired_tasks = [
        'generate_audio_cache',
        'clean_audio_cache',
        'generate_image_cache',
        'clean_image_cache'
    ]
    created_any = False
    for task_name in desired_tasks:
        if not BackgroundTask.query.filter_by(task_name=task_name).first():
            db.session.add(BackgroundTask(task_name=task_name, message='Sẵn sàng', is_enabled=True))
            created_any = True
    if created_any:
        db.session.commit()
        tasks = BackgroundTask.query.all()

    flashcard_containers = LearningContainer.query.filter_by(container_type='FLASHCARD_SET').order_by(LearningContainer.title.asc()).all()

    return render_template('background_tasks.html', tasks=tasks, flashcard_containers=flashcard_containers)

@admin_bp.route('/tasks/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """
    Mô tả: Bật/tắt một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    task.is_enabled = not task.is_enabled
    db.session.commit()
    return jsonify({'success': True, 'is_enabled': task.is_enabled})

@admin_bp.route('/tasks/start/<int:task_id>', methods=['POST'])
def start_task(task_id):
    """
    Mô tả: Bắt đầu một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status != 'running' and task.is_enabled:
        data = request.get_json(silent=True) or {}
        container_id = data.get('container_id') if isinstance(data, dict) else None
        container_scope_ids = None
        scope_label = 'tất cả bộ thẻ Flashcard'

        if container_id not in (None, ''):
            try:
                container_id_int = int(container_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Giá trị container_id không hợp lệ.'}), 400

            selected_container = LearningContainer.query.filter_by(container_id=container_id_int, container_type='FLASHCARD_SET').first()
            if not selected_container:
                return jsonify({'success': False, 'message': 'Không tìm thấy bộ thẻ Flashcard được chọn.'}), 404

            container_scope_ids = [selected_container.container_id]
            scope_label = f"bộ thẻ \"{selected_container.title}\" (ID {selected_container.container_id})"

        task.status = 'running'
        task.message = f"Đang khởi chạy cho {scope_label}..."
        db.session.commit()

        # Chạy tác vụ trong một thread hoặc process riêng
        if task.task_name == 'generate_audio_cache':
            asyncio.run(audio_service.generate_cache_for_all_cards(task, container_ids=container_scope_ids))
        elif task.task_name == 'clean_audio_cache':
            audio_service.clean_orphan_audio_cache(task)
        elif task.task_name == 'generate_image_cache':
            asyncio.run(image_service.generate_images_for_missing_cards(task, container_ids=container_scope_ids))
        elif task.task_name == 'clean_image_cache':
            image_service.clean_orphan_image_cache(task)

        return jsonify({'success': True, 'scope_label': scope_label})

    return jsonify({'success': False, 'message': 'Tác vụ đang chạy hoặc đã bị vô hiệu hóa.'}), 400

@admin_bp.route('/tasks/stop/<int:task_id>', methods=['POST'])
def stop_task(task_id):
    """
    Mô tả: Dừng một tác vụ nền đang chạy.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status == 'running':
        task.stop_requested = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Yêu cầu dừng đã được gửi.'})
    return jsonify({'success': False, 'message': 'Tác vụ không chạy.'})

@admin_bp.route('/settings', methods=['GET', 'POST'])
def manage_system_settings():
    """
    Mô tả: Quản lý các cài đặt hệ thống.
    """
    if request.method == 'POST':
        maintenance_mode = 'maintenance_mode' in request.form
        
        setting = SystemSetting.query.filter_by(key='system_status').first()
        if setting:
            setting.value['maintenance_mode'] = maintenance_mode
            flag_modified(setting, 'value')
        else:
            setting = SystemSetting(key='system_status', value={'maintenance_mode': maintenance_mode})
            db.session.add(setting)
        
        db.session.commit()
        flash('Cài đặt hệ thống đã được cập nhật thành công!', 'success')
        return redirect(url_for('admin.manage_system_settings'))

    system_status_setting = SystemSetting.query.filter_by(key='system_status').first()
    maintenance_mode = False
    if system_status_setting and isinstance(system_status_setting.value, dict):
        maintenance_mode = system_status_setting.value.get('maintenance_mode', False)
        
    return render_template('system_settings.html', maintenance_mode=maintenance_mode)
    
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
            with zipfile.ZipFile(file_path, 'r') as zipf:
                members = zipf.namelist()
                has_uploads = any(member.startswith('uploads/') for member in members)

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

    dataset_options = [
        {
            'key': key,
            'label': config['label'],
            'description': config['description'],
        }
        for key, config in DATASET_CATALOG.items()
    ]

    return render_template(
        'backup_restore.html',
        backup_entries=backup_entries,
        dataset_options=dataset_options,
    )

@admin_bp.route('/backup/database', methods=['POST'])
def create_database_backup():
    """Tạo bản sao lưu cơ sở dữ liệu và lưu trên máy chủ."""

    try:
        backup_folder = _get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_database_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_folder, backup_filename)

        db_path = _resolve_database_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError('Không tìm thấy file cơ sở dữ liệu để sao lưu.')

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(db_path, os.path.basename(db_path))
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
    backup_folder = _get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    return send_file(target_path, as_attachment=True, download_name=os.path.basename(target_path))


def _build_dataset_export_response(dataset_key: str):
    if dataset_key not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    config = DATASET_CATALOG[dataset_key]

    try:
        payload = _collect_dataset_payload(dataset_key)
        backup_folder = _get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mindstack_{dataset_key}_dataset_{timestamp}.zip'
        file_path = os.path.join(backup_folder, filename)

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
    dataset_key = request.form.get('dataset_key', '')
    if not dataset_key:
        flash('Vui lòng chọn gói dữ liệu cần xuất.', 'warning')
        return redirect(url_for('admin.manage_backup_restore'))

    return _build_dataset_export_response(dataset_key)


@admin_bp.route('/backup/export/<string:dataset_key>')
def export_dataset(dataset_key: str):
    return _build_dataset_export_response(dataset_key)


@admin_bp.route('/backup/delete/<path:filename>', methods=['POST'])
def delete_backup_file(filename: str):
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
    """Tạo gói sao lưu toàn bộ dữ liệu (database + uploads) và trả về cho trình duyệt."""

    try:
        db_path = _resolve_database_path()
        uploads_folder = current_app.config.get('UPLOAD_FOLDER')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_full_backup_{timestamp}.zip'

        temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_file.close()

        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(db_path):
                zipf.write(db_path, os.path.basename(db_path))

            if uploads_folder and os.path.exists(uploads_folder):
                base_dir = os.path.dirname(uploads_folder)
                for foldername, _, filenames in os.walk(uploads_folder):
                    for fname in filenames:
                        file_path = os.path.join(foldername, fname)
                        arcname = os.path.relpath(file_path, base_dir)
                        zipf.write(file_path, arcname)

            manifest = {
                'type': 'full',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'includes_uploads': bool(uploads_folder and os.path.exists(uploads_folder)),
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        response = send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=backup_filename,
        )

        @after_this_request
        def _cleanup_temp_file(response):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass
            return response

        response.headers['X-Mindstack-Backup'] = 'full'
        return response
    except Exception as exc:
        current_app.logger.error('Lỗi khi tạo bản sao lưu toàn bộ: %s', exc)
        flash(f'Lỗi khi tạo bản sao lưu toàn bộ: {exc}', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))


@admin_bp.route('/restore-dataset/<string:dataset_key>', methods=['POST'])
@admin_bp.route('/restore-dataset', methods=['POST'])
def restore_dataset(dataset_key: Optional[str] = None):
    if not dataset_key:
        dataset_key = request.form.get('dataset_key', '')

    if dataset_key not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    upload = request.files.get('dataset_file')
    if not upload or upload.filename == '':
        flash('Vui lòng chọn file dữ liệu để khôi phục.', 'warning')
        return redirect(url_for('admin.manage_backup_restore'))

    try:
        payload = _load_dataset_payload(upload, dataset_key)
        if not payload:
            flash('Không tìm thấy dữ liệu hợp lệ trong file đã tải lên.', 'warning')
            return redirect(url_for('admin.manage_backup_restore'))

        _apply_dataset_restore(dataset_key, payload)
        flash('Đã khôi phục dữ liệu thành công cho phần được chọn!', 'success')
    except Exception as exc:
        current_app.logger.error('Lỗi khi khôi phục dataset %s: %s', dataset_key, exc)
        flash(f'Lỗi khi khôi phục dữ liệu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))

@admin_bp.route('/restore/<string:filename>', methods=['POST'])
@admin_bp.route('/restore', methods=['POST'])
def restore_backup(filename: Optional[str] = None):
    """
    Mô tả: Khôi phục dữ liệu từ một bản sao lưu đã chọn.
    """
    try:
        if not filename:
            filename = request.form.get('filename', '')

        backup_folder = _get_backup_folder()
        backup_path = safe_join(backup_folder, filename)

        if not backup_path or not os.path.exists(backup_path):
            flash('File sao lưu không tồn tại.', 'danger')
            return redirect(url_for('admin.manage_backup_restore'))

        restore_database = request.form.get('restore_database', 'on') == 'on'
        restore_uploads = request.form.get('restore_uploads', 'on') == 'on'

        db_path = None
        if restore_database:
            # Đóng database connection để có thể ghi đè file
            db.session.close()
            db.engine.dispose()

            db_path = _resolve_database_path()

        with zipfile.ZipFile(backup_path, 'r') as zipf:
            members = zipf.namelist()
            temp_dir = tempfile.mkdtemp(prefix='mindstack_restore_')
            try:
                if restore_database:
                    db_member = next((m for m in members if db_path and os.path.basename(db_path) in m), None)
                    if not db_member:
                        raise RuntimeError('Gói sao lưu không chứa file cơ sở dữ liệu hợp lệ.')

                    zipf.extract(db_member, temp_dir)
                    extracted_db_path = os.path.join(temp_dir, db_member)
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    shutil.copy2(extracted_db_path, db_path)

                if restore_uploads:
                    uploads_folder = current_app.config.get('UPLOAD_FOLDER')
                    if uploads_folder and any(member.startswith('uploads/') for member in members):
                        zipf.extractall(temp_dir)
                        source_uploads = os.path.join(temp_dir, 'uploads')
                        if os.path.exists(source_uploads):
                            shutil.rmtree(uploads_folder, ignore_errors=True)
                            shutil.copytree(source_uploads, uploads_folder, dirs_exist_ok=True)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        flash('Đã khôi phục dữ liệu thành công!', 'success')
    except Exception as e:
        current_app.logger.error(f"Lỗi khi khôi phục dữ liệu: {e}")
        flash(f'Lỗi khi khôi phục dữ liệu: {e}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))

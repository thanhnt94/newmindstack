# File: Mindstack/web/mindstack_app/modules/admin/routes.py
# Version: 2.5
# Mục đích: Chứa các route và logic cho bảng điều khiển admin tổng quan.
# ĐÃ THÊM: Route và logic để quản lý việc sao lưu và khôi phục dữ liệu.

from flask import render_template, redirect, url_for, flash, abort, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from ...models import db, User, LearningContainer, LearningItem, ApiKey, BackgroundTask, SystemSetting
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm.attributes import flag_modified
import shutil
import os
import zipfile
from uuid import uuid4
from werkzeug.utils import secure_filename, safe_join

from ..learning.flashcard_learning.audio_service import AudioService
from ..learning.flashcard_learning.image_service import ImageService

audio_service = AudioService()
image_service = ImageService()

from . import admin_bp # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.

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

    return render_template('dashboard.html', stats_data=stats_data)


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
    backup_folder = os.path.join(current_app.root_path, 'backups')
    backup_files = [f for f in os.listdir(backup_folder) if f.endswith('.zip')] if os.path.exists(backup_folder) else []
    
    # Sắp xếp theo ngày tạo mới nhất
    backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_folder, x)), reverse=True)
    
    return render_template('backup_restore.html', backup_files=backup_files)

@admin_bp.route('/backup', methods=['POST'])
def create_backup():
    """
    Mô tả: Tạo một bản sao lưu mới.
    """
    try:
        backup_folder = os.path.join(current_app.root_path, 'backups')
        os.makedirs(backup_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"mindstack_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_folder, backup_filename)
        
        # Tạo file zip
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Sao lưu database
            db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')
            if os.path.exists(db_path):
                zipf.write(db_path, os.path.basename(db_path))
            
            # Sao lưu thư mục uploads
            uploads_folder = current_app.config.get('UPLOAD_FOLDER')
            if os.path.exists(uploads_folder):
                for foldername, subfolders, filenames in os.walk(uploads_folder):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(uploads_folder)))
        
        flash('Đã tạo bản sao lưu thành công!', 'success')
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tạo bản sao lưu: {e}")
        flash(f'Lỗi khi tạo bản sao lưu: {e}', 'danger')
        
    return redirect(url_for('admin.manage_backup_restore'))

@admin_bp.route('/restore/<string:filename>', methods=['POST'])
def restore_backup(filename):
    """
    Mô tả: Khôi phục dữ liệu từ một bản sao lưu đã chọn.
    """
    try:
        backup_folder = os.path.join(current_app.root_path, 'backups')
        backup_path = os.path.join(backup_folder, filename)
        
        if not os.path.exists(backup_path):
            flash('File sao lưu không tồn tại.', 'danger')
            return redirect(url_for('admin.manage_backup_restore'))
        
        # Đóng database connection để có thể ghi đè file
        db.session.close()
        db.engine.dispose()
        
        # Giải nén file sao lưu
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(current_app.root_path)
            
        flash('Đã khôi phục dữ liệu thành công!', 'success')
    except Exception as e:
        current_app.logger.error(f"Lỗi khi khôi phục dữ liệu: {e}")
        flash(f'Lỗi khi khôi phục dữ liệu: {e}', 'danger')
    
    return redirect(url_for('admin.manage_backup_restore'))
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

from ..learning.flashcard_learning.audio_service import AudioService
audio_service = AudioService()

from . import admin_bp # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.

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

@admin_bp.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền.
    """
    tasks = BackgroundTask.query.all()
    if not tasks:
        # Nếu chưa có tác vụ nào, tạo các tác vụ mặc định
        task1 = BackgroundTask(task_name='generate_audio_cache', message='Sẵn sàng', is_enabled=True)
        task2 = BackgroundTask(task_name='clean_audio_cache', message='Sẵn sàng', is_enabled=True)
        db.session.add_all([task1, task2])
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
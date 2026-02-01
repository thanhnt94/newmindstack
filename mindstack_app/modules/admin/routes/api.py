# File: mindstack_app/modules/admin/routes/api.py
import asyncio
import os
from flask import request, jsonify
from flask_login import current_user
from mindstack_app.models import db, BackgroundTask, BackgroundTaskLog, LearningContainer, User, AppSettings
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.modules.AI.services.explanation_service import (
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    generate_ai_explanations,
)
from mindstack_app.services.template_service import TemplateService
from .. import admin_bp as blueprint

# ... (existing tasks/settings API routes)

@blueprint.route('/modules/toggle', methods=['POST'])
def toggle_module():
    """API để bật/tắt một module."""
    data = request.get_json()
    module_key = data.get('key')
    
    if not module_key:
        return jsonify({'success': False, 'message': 'Missing module key'}), 400

    if module_key in ['admin', 'auth', 'landing']:
        return jsonify({'success': False, 'message': 'Không thể tắt module hệ thống cốt lõi'}), 400

    current_state = AppSettings.get(f"MODULE_ENABLED_{module_key}", True)
    new_state = not current_state
    
    AppSettings.set(f"MODULE_ENABLED_{module_key}", new_state, user_id=current_user.user_id)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'new_state': new_state,
        'message': f"Đã {'bật' if new_state else 'tắt'} module {module_key}"
    })

@blueprint.route('/templates/update', methods=['POST'])
def update_template_settings():
    """
    API endpoint to update template settings via JSON.
    """
    data = request.get_json()
    updates = data.get('updates', {})
    
    if not updates:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    try:
        # Currently the UI sends 'global_system' -> version
        if 'global_system' in updates:
            version = updates['global_system']
            TemplateService.set_active_global_version(version)
            return jsonify({'success': True, 'message': f'Đã kích hoạt giao diện: {version}'})
            
        return jsonify({'success': True, 'message': 'Settings saved (no changes detected).'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500

@blueprint.route('/content-config/save-general', methods=['POST'])
def save_general_config():
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        for key, val in settings.items():
            AppSettings.set(key, val, category='content') 
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/reset-general', methods=['POST'])
def reset_general_config():
    keys_to_reset = ['CONTENT_MAX_UPLOAD_SIZE', 'CONTENT_ALLOWED_EXTENSIONS', 'CONTENT_ENABLE_PUBLIC_SHARING']
    
    try:
        for k in keys_to_reset:
            setting = AppSettings.query.get(k)
            if setting:
                db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã khôi phục mặc định chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ... (existing code)

@blueprint.route('/settings/browse-directories', methods=['GET'])
def browse_directories_api():
    """
    API to browse server directories.
    Query Params:
        path: current path to list (default: root)
    """
    current_path = request.args.get('path', 'C:\\')
    
    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        return jsonify({'success': False, 'message': 'Path not found'}), 404

    try:
        items = []
        with os.scandir(current_path) as it:
            for entry in it:
                if entry.is_dir():
                    items.append({
                        'name': entry.name,
                        'path': entry.path,
                        'type': 'directory'
                    })
        
        # Sort by name
        items.sort(key=lambda x: x['name'].lower())
        
        # Add parent directory option if not at root
        parent_path = os.path.dirname(current_path)
        if parent_path and parent_path != current_path:
             items.insert(0, {
                'name': '..',
                'path': parent_path,
                'type': 'directory'
            })

        return jsonify({
            'success': True,
            'current_path': current_path,
            'items': items
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/settings/create-directory', methods=['POST'])
def create_directory_api():
    """
    API to create a new directory.
    JSON Body:
        parent_path: parent path
        folder_name: new folder name
    """
    data = request.get_json()
    if not data:
         return jsonify({'success': False, 'message': 'No data provided'}), 400

    parent_path = data.get('parent_path')
    folder_name = data.get('folder_name')

    if not parent_path or not folder_name:
        return jsonify({'success': False, 'message': 'Missing path or name'}), 400

    new_path = os.path.join(parent_path, folder_name)

    if os.path.exists(new_path):
        return jsonify({'success': False, 'message': 'Directory already exists'}), 400

    try:
        os.makedirs(new_path)
        return jsonify({
            'success': True,
            'message': 'Directory created successfully',
            'path': new_path
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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

@blueprint.route('/tasks/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    task = BackgroundTask.query.get_or_404(task_id)
    task.is_enabled = not task.is_enabled
    db.session.commit()
    return success_response(data={'is_enabled': task.is_enabled})

@blueprint.route('/tasks/start/<int:task_id>', methods=['POST'])
def start_task(task_id):
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
        scope_label = f"{type_label} '{selected_container.title}' (ID {selected_container.container_id})"

    if task.task_name == 'generate_ai_explanations' and scope_label == 'tất cả bộ học liệu':
        scope_label = 'tất cả học liệu'

    task.status = 'running'
    task.message = f"Đang khởi chạy cho {scope_label}..."
    db.session.commit()

    from mindstack_app.modules.vocab_flashcard.services import AudioService, ImageService
    from mindstack_app.modules.quiz.individual.services.audio_service import QuizAudioService
    
    audio_service = AudioService()
    image_service = ImageService()
    quiz_audio_service = QuizAudioService()

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

@blueprint.route('/tasks/stop/<int:task_id>', methods=['POST'])
def stop_task(task_id):
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status == 'running':
        task.stop_requested = True
        task.message = 'Đã nhận yêu cầu dừng, sẽ kết thúc sau bước hiện tại.'
        db.session.commit()
        return success_response(message='Yêu cầu dừng đã được gửi.')
    return error_response('Tác vụ không chạy.', 'BAD_REQUEST', 400)

@blueprint.route('/tasks/<int:task_id>/logs/data', methods=['GET'])
def fetch_task_logs(task_id: int):
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

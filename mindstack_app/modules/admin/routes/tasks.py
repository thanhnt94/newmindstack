# File: mindstack_app/modules/admin/routes/tasks.py
import asyncio
from flask import render_template, request, jsonify
from mindstack_app.models import db, BackgroundTask, BackgroundTaskLog, LearningContainer
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.modules.AI.services.explanation_service import (
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    generate_ai_explanations,
)
from .. import blueprint

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

@blueprint.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền.
    """
    tasks = BackgroundTask.query.all()
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
        scope_label = f"{type_label} \"{selected_container.title}\" (ID {selected_container.container_id})"

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


@blueprint.route('/tasks/<int:task_id>/logs', methods=['GET'])
def view_task_logs(task_id: int):
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

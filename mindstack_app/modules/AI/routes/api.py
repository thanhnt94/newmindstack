# File: mindstack_app/modules/AI/routes/api.py
import threading
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
import mistune
from .. import blueprint
from ..services.ai_manager import get_ai_service
from ..logics.prompts import get_formatted_prompt
from ..models import db, ApiKey, AiTokenLog
from mindstack_app.models import LearningItem, BackgroundTask, BackgroundTaskLog, AppSettings
from mindstack_app.utils.html_sanitizer import sanitize_rich_text
from mindstack_app.core.error_handlers import error_response, success_response

@blueprint.route('/ai/get-ai-response', methods=['POST'])
@login_required
def get_ai_response():
    """
    Endpoint chính để nhận yêu cầu từ frontend và trả về phản hồi từ AI.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Yêu cầu không hợp lệ.'}), 400

    prompt_type = data.get('prompt_type', 'explanation')
    item_id = data.get('item_id')
    custom_question = data.get('custom_question')
    force_regenerate = data.get('force_regenerate', False)

    if not item_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin item_id.'}), 400

    item = LearningItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Không tìm thấy học liệu.'}), 404

    if prompt_type == 'explanation' and item.ai_explanation and not force_regenerate:
        html_content = sanitize_rich_text(mistune.html(item.ai_explanation))
        return jsonify({'success': True, 'response': html_content})

    ai_client = get_ai_service()
    if not ai_client:
        return jsonify({'success': False, 'message': 'Dịch vụ AI chưa được cấu hình (thiếu API key).'}), 503

    final_prompt = get_formatted_prompt(item, purpose=prompt_type, custom_question=custom_question)
    
    if not final_prompt:
        return jsonify({'success': False, 'message': 'Không thể tạo prompt cho loại học liệu này.'}), 400
    
    try:
        item_info = f"{item.item_type} ID {item.item_id}"
        success, ai_response = ai_client.generate_content(
            final_prompt, 
            feature=prompt_type,
            context_ref=item_info
        )

        if not success:
            return jsonify({'success': False, 'message': ai_response}), 503

        if prompt_type == 'explanation':
            html_content = sanitize_rich_text(mistune.html(ai_response))
            item.ai_explanation = html_content
            db.session.commit()
            return jsonify({'success': True, 'response': html_content})

        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý yêu cầu AI cho item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi phía máy chủ khi xử lý yêu cầu AI.'}), 500

# --- Admin API Routes ---

@blueprint.route('/admin/ai/settings/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    provider = request.form.get('AI_PROVIDER')
    gemini_model = request.form.get('GEMINI_MODEL')
    hf_model = request.form.get('HUGGINGFACE_MODEL')
    
    if gemini_model == 'custom':
        gemini_model = request.form.get('GEMINI_MODEL_custom')

    if hf_model == 'custom':
        hf_model = request.form.get('HUGGINGFACE_MODEL_custom')

    try:
        if provider: AppSettings.set('AI_PROVIDER', provider, category='ai')
        if gemini_model: AppSettings.set('GEMINI_MODEL', gemini_model, category='ai')
        if hf_model: AppSettings.set('HUGGINGFACE_MODEL', hf_model, category='ai')

        db.session.commit()
        flash('Đã cập nhật cấu hình AI Coach thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return redirect(url_for('.dashboard'))

@blueprint.route('/admin/ai/keys/delete/<int:key_id>', methods=['POST'])
@login_required
def delete_key(key_id):
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    flash('Đã xóa API key thành công.', 'success')
    return redirect(url_for('.dashboard'))

@blueprint.route('/admin/ai/keys/check/<int:key_id>', methods=['POST'])
@login_required
def check_key_quota(key_id):
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    key = ApiKey.query.get_or_404(key_id)
    if key.provider != 'gemini':
        return jsonify({'success': False, 'message': 'Chỉ hỗ trợ check quota cho Gemini.'})

    try:
        import google.generativeai as genai
        from google.api_core import exceptions as google_exceptions
        genai.configure(api_key=key.key_value)
        list(genai.list_models(page_size=1))
        key.is_exhausted = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Key hoạt động tốt (Active).'})
    except google_exceptions.ResourceExhausted:
        key.is_exhausted = True
        db.session.commit()
        return jsonify({'success': False, 'message': 'Key đã hết quota.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi kiểm tra: {str(e)}'})

@blueprint.route('/admin/ai/models/gemini', methods=['GET'])
@login_required
def fetch_gemini_models_api():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    try:
        from ..engines.gemini_client import GeminiClient
        raw_list = GeminiClient.get_available_models()
        models = [{'id': m, 'display_name': m} for m in raw_list]
        return jsonify({'success': True, 'models': models})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/admin/ai/autogen/start', methods=['POST'])
@login_required
def start_autogen():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    from ..services.autogen_service import run_autogen_background
    
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        set_id = data.get('set_id')
        api_delay = int(data.get('api_delay', 2))
        max_items = int(data.get('max_items', 25))
        
        if not content_type or not set_id:
            return error_response('Missing required parameters', 'BAD_REQUEST', 400)
        
        task = BackgroundTask.query.filter_by(task_name='autogen_content').first()
        if task and task.status == 'running':
             return error_response('A task is already running', 'CONFLICT', 409)
        
        if not task:
            task = BackgroundTask(task_name='autogen_content')
            db.session.add(task)
            
        task.status = 'pending'
        task.progress = 0
        task.total = 0
        task.message = 'Initializing...'
        task.stop_requested = False
        db.session.commit()

        app = current_app._get_current_object()
        thread = threading.Thread(
            target=run_autogen_background,
            args=(app, content_type, set_id, api_delay, max_items, task.task_id),
            name='autogen_content_thread'
        )
        thread.daemon = True
        thread.start()
        return success_response(message='Task started', data={'task_id': task.task_id})
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/admin/ai/autogen/status', methods=['GET'])
@login_required
def get_autogen_status():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    if not task:
        return success_response(data={'active': False})
    return success_response(data={
        'active': True,
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'total': task.total,
        'message': task.message,
        'last_updated': task.last_updated.isoformat() if task.last_updated else None
    })

@blueprint.route('/admin/ai/autogen/logs', methods=['GET'])
@login_required
def get_autogen_logs():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    if not task:
        return success_response(data={'logs': []})
    logs = BackgroundTaskLog.query.filter_by(task_id=task.task_id).order_by(BackgroundTaskLog.created_at.asc()).all()
    log_data = []
    from datetime import timezone
    for log in logs:
        dt = log.created_at
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        log_data.append({
            'timestamp': dt.isoformat() if dt else None,
            'message': log.message,
            'status': log.status
        })
    return success_response(data={'logs': log_data})

@blueprint.route('/admin/ai/autogen/get-sets/<content_type>', methods=['GET'])
@login_required
def get_sets_for_autogen(content_type):
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    from ..services.autogen_service import get_sets_with_missing_content
    result = get_sets_with_missing_content(content_type)
    return success_response(data=result)

@blueprint.route('/admin/ai/test_chat', methods=['POST'])
@login_required
def test_hop_chat():
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    try:
        data = request.get_json()
        provider = data.get('provider', 'gemini')
        model = data.get('model', '')
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt không được để trống.'}), 400

        from ..engines.gemini_client import GeminiClient
        from ..engines.huggingface_client import HuggingFaceClient
        
        from datetime import datetime
        start_time = datetime.now()
        response_text = ""
        if provider == 'gemini':
            client = GeminiClient(model_name=model or 'gemini-2.0-flash-lite-001')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        elif provider == 'huggingface':
            client = HuggingFaceClient(model_name=model or 'google/gemma-7b-it')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        else:
            from ..services.ai_manager import get_ai_service
            service = get_ai_service()
            _, response_text = service.generate_content(prompt, feature='test_chat', context_ref='admin_test')

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)
        return jsonify({
            'success': True,
            'response': response_text,
            'provider': provider,
            'model': model or 'default',
            'duration_ms': duration
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    

# File: mindstack_app/modules/AI/routes/admin.py
# Purpose: Admin Control Panel for AI Module (formerly api_key_management)

from flask import Blueprint, abort, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, timedelta

from mindstack_app.modules.AI.forms import ApiKeyForm
from mindstack_app.modules.AI.models import ApiKey, AiTokenLog
from mindstack_app.models import db, BackgroundTask, AppSettings, BackgroundTaskLog
from mindstack_app.core.error_handlers import error_response, success_response

# Create a separate blueprint for Admin routes to have a distinct URL prefix
admin_bp = Blueprint('ai_admin', __name__, url_prefix='/admin/ai')

@admin_bp.before_request
def admin_required():
    """
    Middleware to ensure only admins access this module.
    """
    # Allow static files to be accessed without login checks if needed
    if request.endpoint and request.endpoint.endswith('static'):
        return

    if not current_user.is_authenticated:
        flash('Vui lòng đăng nhập.', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        abort(403)

@admin_bp.route('/', methods=['GET', 'POST'])
def dashboard():
    """
    Dashboard AI Coach - Keys, Settings, Logs.
    """
    # 1. Fetch API Keys
    keys = ApiKey.query.order_by(ApiKey.key_id.asc()).all()
    
    # 2. Fetch Usage Logs with Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = AiTokenLog.query.order_by(desc(AiTokenLog.timestamp)).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # 3. Fetch Chart Data (Last 7 Days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    stats_query = db.session.query(
        func.date(AiTokenLog.timestamp).label('date'),
        AiTokenLog.model_name,
        func.count(AiTokenLog.log_id),
        func.sum(AiTokenLog.input_tokens),
        func.sum(AiTokenLog.output_tokens)
    ).filter(AiTokenLog.timestamp >= seven_days_ago) \
     .group_by('date', AiTokenLog.model_name).all()
     
    dates_set = set()
    models_set = set()
    map_requests = {} 
    map_tokens = {}

    for date_str, model_name, count, sum_in, sum_out in stats_query:
        if not date_str or not model_name: continue
        dates_set.add(date_str)
        models_set.add(model_name)
        
        if date_str not in map_requests: map_requests[date_str] = {}
        if date_str not in map_tokens: map_tokens[date_str] = {}
        
        map_requests[date_str][model_name] = count
        total_tokens = (sum_in or 0) + (sum_out or 0)
        map_tokens[date_str][model_name] = total_tokens
    
    sorted_dates = sorted(list(dates_set))
    if not sorted_dates:
        sorted_dates = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(8)]
    
    datasets_requests = []
    datasets_tokens = []
    
    for model in sorted(list(models_set)):
        counts_req = []
        counts_tok = []
        for d in sorted_dates:
            counts_req.append(map_requests.get(d, {}).get(model, 0))
            counts_tok.append(map_tokens.get(d, {}).get(model, 0))
            
        datasets_requests.append({ 'label': model, 'data': counts_req })
        datasets_tokens.append({ 'label': model, 'data': counts_tok })
    
    chart_payload = {
        'labels': sorted_dates,
        'datasets_requests': datasets_requests,
        'datasets_tokens': datasets_tokens
    }

    # 4. Fetch Current AI Settings
    current_provider = AppSettings.get('AI_PROVIDER', 'gemini')
    gemini_model = AppSettings.get('GEMINI_MODEL', 'gemini-1.5-flash')
    hf_model = AppSettings.get('HUGGINGFACE_MODEL', 'google/gemma-7b-it')
    
    settings = {
        'provider': current_provider,
        'gemini_model': gemini_model,
        'hf_model': hf_model
    }

    # IMPORTANT: We need to copy templates from old module to themes/admin/templates/ai/admin/
    # For now, we reuse the old path 'admin/api_keys/api_keys.html' but we should assume 
    # it will be available.
    return render_template('admin/api_keys/api_keys.html', keys=keys, logs=logs, pagination=pagination, ai_settings=settings, chart_data=chart_payload)

@admin_bp.route('/settings/update', methods=['POST'])
def update_settings():
    """
    Update AI configurations.
    """
    provider = request.form.get('AI_PROVIDER')
    gemini_model = request.form.get('GEMINI_MODEL')
    hf_model = request.form.get('HUGGINGFACE_MODEL')
    
    if req_gemini_custom := request.form.get('GEMINI_MODEL_custom'):
        if gemini_model == 'custom':
            gemini_model = req_gemini_custom

    if req_hf_custom := request.form.get('HUGGINGFACE_MODEL_custom'):
        if hf_model == 'custom':
            hf_model = req_hf_custom

    try:
        if provider: AppSettings.set('AI_PROVIDER', provider, category='ai', description='AI Coach Setting')
        if gemini_model: AppSettings.set('GEMINI_MODEL', gemini_model, category='ai', description='AI Coach Setting')
        if hf_model: AppSettings.set('HUGGINGFACE_MODEL', hf_model, category='ai', description='AI Coach Setting')

        db.session.commit()
        flash('Đã cập nhật cấu hình AI Coach thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return redirect(url_for('.dashboard'))

@admin_bp.route('/keys/add', methods=['GET', 'POST'])
def add_key():
    """
    Add new API key.
    """
    form = ApiKeyForm()
    form.submit.label.text = 'Thêm API Key'
    if form.validate_on_submit():
        new_key = ApiKey(
            provider=form.provider.data,
            key_value=form.key_value.data,
            notes=form.notes.data,
            is_active=form.is_active.data,
            is_exhausted=False 
        )
        db.session.add(new_key)
        db.session.commit()
        flash('Đã thêm API key mới thành công!', 'success')
        return redirect(url_for('.dashboard'))
    return render_template('admin/api_keys/add_edit_api_key.html', form=form, title='Thêm API Key mới')

@admin_bp.route('/keys/edit/<int:key_id>', methods=['GET', 'POST'])
def edit_key(key_id):
    """
    Edit existing API key.
    """
    key = ApiKey.query.get_or_404(key_id)
    form = ApiKeyForm(obj=key)
    form.submit.label.text = 'Cập nhật API Key'
    if form.validate_on_submit():
        key.provider = form.provider.data
        key.key_value = form.key_value.data
        key.notes = form.notes.data
        key.is_active = form.is_active.data
        key.is_exhausted = form.is_exhausted.data
        db.session.commit()
        flash('Đã cập nhật thông tin API key!', 'success')
        return redirect(url_for('.dashboard'))
    return render_template('admin/api_keys/add_edit_api_key.html', form=form, title='Chỉnh sửa API Key')

@admin_bp.route('/keys/delete/<int:key_id>', methods=['POST'])
def delete_key(key_id):
    """
    Delete API key.
    """
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    flash('Đã xóa API key thành công.', 'success')
    return redirect(url_for('.dashboard'))


# ==================== AUTO-GENERATE ROUTES ====================

@admin_bp.route('/autogen/get-sets/<content_type>', methods=['GET'])
def get_sets_for_autogen(content_type):
    from mindstack_app.modules.AI.services.autogen_service import get_sets_with_missing_content
    result = get_sets_with_missing_content(content_type)
    return success_response(data=result)

@admin_bp.route('/autogen/start', methods=['POST'])
def start_autogen():
    from mindstack_app.modules.AI.services.autogen_service import run_autogen_background
    import threading
    
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        set_id = data.get('set_id')
        api_delay = int(data.get('api_delay', 2))
        max_items = int(data.get('max_items', 25))
        
        if not content_type or not set_id:
            return error_response('Missing required parameters', 'BAD_REQUEST', 400)
        
        task = BackgroundTask.query.filter_by(task_name='autogen_content').first()
        
        if task:
            if task.status == 'running':
                 return error_response('A task is already running', 'CONFLICT', 409, details={'task_id': task.task_id})
            
            task.status = 'pending'
            task.progress = 0
            task.total = 0
            task.message = 'Initializing...'
            task.stop_requested = False
            task.is_enabled = True
        else:
            task = BackgroundTask(
                task_name='autogen_content',
                status='pending',
                progress=0,
                total=0,
                message='Initializing...', 
                is_enabled=True
            )
            db.session.add(task)

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
        db.session.rollback()
        return error_response(str(e), 'SERVER_ERROR', 500)

@admin_bp.route('/autogen/status', methods=['GET'])
def get_autogen_status():
    import threading
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    
    if not task:
        return success_response(data={'active': False})
    
    if task.status in ['running', 'pending']:
        is_thread_alive = False
        for t in threading.enumerate():
            if t.name == 'autogen_content_thread':
                is_thread_alive = True
                break
        
        if not is_thread_alive:
            task.status = 'interrupted'
            task.message = f"Task interrupted (server restart or crash). Last state: {task.message}"
            db.session.commit()
    
    return success_response(data={
        'active': True,
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'total': task.total,
        'message': task.message,
        'last_updated': task.last_updated.isoformat() if task.last_updated else None
    })

@admin_bp.route('/autogen/logs', methods=['GET'])
def get_autogen_logs():
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


@admin_bp.route('/redirect-item/<int:item_id>', methods=['GET'])
def redirect_to_item_context(item_id):
    from mindstack_app.modules.learning.models import LearningItem
    
    item = LearningItem.query.get_or_404(item_id)
    
    if item.item_type in ['QUIZ_MCQ', 'QUIZ_TEXT']:
        return redirect(url_for('content_management.content_management_quizzes.edit_quiz_item', 
                                set_id=item.container_id, item_id=item.item_id))
                                
    elif item.item_type == 'FLASHCARD':
        return redirect(url_for('content_management.content_management_flashcards.edit_flashcard_item', 
                                set_id=item.container_id, item_id=item.item_id))
    
    flash(f"Unknown item type: {item.item_type}", "warning")
    return redirect(url_for('.dashboard'))

@admin_bp.route('/test_chat', methods=['POST'])
def test_hop_chat():
    try:
        data = request.get_json()
        provider = data.get('provider', 'gemini')
        model = data.get('model', '')
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt không được để trống.'}), 400

        from mindstack_app.modules.AI.engines.gemini_client import GeminiClient
        from mindstack_app.modules.AI.engines.huggingface_client import HuggingFaceClient
        
        start_time = datetime.now()
        response_text = ""
        
        if provider == 'gemini':
            client = GeminiClient(model_name=model or 'gemini-2.0-flash-lite-001')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        elif provider == 'huggingface':
            client = HuggingFaceClient(model_name=model or 'google/gemma-7b-it')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        else:
            from mindstack_app.modules.AI.services.ai_manager import get_ai_service
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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

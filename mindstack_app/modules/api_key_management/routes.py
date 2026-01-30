# File: mindstack_app/modules/admin/api_key_management/routes.py
# Phiên bản: 1.1
# Mục đích: Chứa các route và logic cho việc quản lý API keys.

from flask import abort, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from . import blueprint
from .forms import ApiKeyForm
from mindstack_app.models import db, ApiKey, AiTokenLog, BackgroundTask, AppSettings
from mindstack_app.core.error_handlers import error_response, success_response

@blueprint.before_request
def admin_required():
    """
    Mô tả: Middleware để đảm bảo chỉ có admin mới truy cập được module này.
    """
    # Allow static files to be accessed without login checks
    if request.endpoint and request.endpoint == 'api_key_management.static':
        return

    if not current_user.is_authenticated:
        flash('Vui lòng đăng nhập.', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        abort(403)

@blueprint.route('/', methods=['GET', 'POST'])
def list_api_keys():
    """
    Mô tả: Dashboard AI Coach - Hiển thị Keys, Settings và Log hoạt động.
    """
    # 1. Fetch API Keys
    keys = ApiKey.query.order_by(ApiKey.key_id.asc()).all()
    
    # 2. Fetch Usage Logs with Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = AiTokenLog.query.order_by(desc(AiTokenLog.timestamp)).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # 3. Fetch Chart Data (Last 7 Days) - Grouped by Model
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    # Query: Date, Model, Count, Sum(InputTokens), Sum(OutputTokens)
    stats_query = db.session.query(
        func.date(AiTokenLog.timestamp).label('date'),
        AiTokenLog.model_name,
        func.count(AiTokenLog.log_id),
        func.sum(AiTokenLog.input_tokens),
        func.sum(AiTokenLog.output_tokens)
    ).filter(AiTokenLog.timestamp >= seven_days_ago)\
     .group_by('date', AiTokenLog.model_name).all()
     
    # Transform data for Chart.js
    dates_set = set()
    models_set = set()
    
    # Maps for different metrics
    # 'YYYY-MM-DD' -> { 'model_a': 10 }
    map_requests = {} 
    # 'YYYY-MM-DD'-> { 'model_a': 5000 }
    map_tokens = {}

    for date_str, model_name, count, sum_in, sum_out in stats_query:
        if not date_str or not model_name: continue
        dates_set.add(date_str)
        models_set.add(model_name)
        
        if date_str not in map_requests: map_requests[date_str] = {}
        if date_str not in map_tokens: map_tokens[date_str] = {}
        
        map_requests[date_str][model_name] = count
        # Total tokens
        total_tokens = (sum_in or 0) + (sum_out or 0)
        map_tokens[date_str][model_name] = total_tokens
    
    # Sort labels (Dates)
    sorted_dates = sorted(list(dates_set))
    if not sorted_dates:
        sorted_dates = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(8)]
    
    # Build Datasets lists
    datasets_requests = []
    datasets_tokens = []
    
    for model in sorted(list(models_set)):
        counts_req = []
        counts_tok = []
        for d in sorted_dates:
            counts_req.append(map_requests.get(d, {}).get(model, 0))
            counts_tok.append(map_tokens.get(d, {}).get(model, 0))
            
        # Common structure
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

    return render_template('admin/api_keys/api_keys.html', keys=keys, logs=logs, pagination=pagination, ai_settings=settings, chart_data=chart_payload)

@blueprint.route('/update_settings', methods=['POST'])
def update_ai_settings():
    """
    Mô tả: Xử lý form cập nhật configuration cho AI Coach.
    """
    provider = request.form.get('AI_PROVIDER')
    gemini_model = request.form.get('GEMINI_MODEL')
    hf_model = request.form.get('HUGGINGFACE_MODEL')
    
    # Custom input logic (fallback to custom if selected, but actually our new UI 
    # uses hidden inputs that already resolve to the final string, so we just take the main input)
    # Check for legacy custom input mapping if needed, 
    # but based on previous refactor, 'gemini_model' hidden input holds the full CSV string.
    
    # Safety Check
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

    return redirect(url_for('.list_api_keys'))

@blueprint.route('/add', methods=['GET', 'POST'])
def add_api_key():
    """
    Mô tả: Thêm một API key mới.
    """
    form = ApiKeyForm()
    form.submit.label.text = 'Thêm API Key'
    if form.validate_on_submit():
        new_key = ApiKey(
            provider=form.provider.data,
            key_value=form.key_value.data,
            notes=form.notes.data,
            is_active=form.is_active.data,
            is_exhausted=False # Mới thêm thì chưa cạn kiệt
        )
        db.session.add(new_key)
        db.session.commit()
        flash('Đã thêm API key mới thành công!', 'success')
        return redirect(url_for('.list_api_keys'))
    return render_template('admin/api_keys/add_edit_api_key.html', form=form, title='Thêm API Key mới')

@blueprint.route('/edit/<int:key_id>', methods=['GET', 'POST'])
def edit_api_key(key_id):
    """
    Mô tả: Chỉnh sửa một API key đã có.
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
        return redirect(url_for('.list_api_keys'))
    return render_template('admin/api_keys/add_edit_api_key.html', form=form, title='Chỉnh sửa API Key')

@blueprint.route('/delete/<int:key_id>', methods=['POST'])
def delete_api_key(key_id):
    """
    Mô tả: Xóa một API key.
    """
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    flash('Đã xóa API key thành công.', 'success')
    return redirect(url_for('.list_api_keys'))


# ==================== AUTO-GENERATE ROUTES ====================

@blueprint.route('/autogen/get-sets/<content_type>', methods=['GET'])
def get_sets_for_autogen(content_type):
    """
    Mô tả: Lấy danh sách quiz sets hoặc flashcard sets với thông tin missing content.
    """
    from .autogen_service import get_sets_with_missing_content
    
    result = get_sets_with_missing_content(content_type)
    return success_response(data=result)


@blueprint.route('/autogen/start', methods=['POST'])
def start_autogen():
    """
    Mô tả: Bắt đầu quá trình auto-generate content (Background Task).
    """
    from .autogen_service import run_autogen_background
    import threading
    from flask import current_app
    
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        set_id = data.get('set_id')
        api_delay = int(data.get('api_delay', 2))
        max_items = int(data.get('max_items', 25))
        
        if not content_type or not set_id:
            return error_response('Missing required parameters', 'BAD_REQUEST', 400)
        
        # Check for existing task record (Singleton pattern for this task name)
        task = BackgroundTask.query.filter_by(task_name='autogen_content').first()
        
        if task:
            # If exists, check if running
            if task.status == 'running':
                 return error_response('A task is already running', 'CONFLICT', 409, details={'task_id': task.task_id})
            
            # Reset existing task for new run
            task.status = 'pending'
            task.progress = 0
            task.total = 0
            task.message = 'Initializing...'
            task.stop_requested = False
            task.is_enabled = True
        else:
            # Create new task record if never existed
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

        # Start background thread
        # We need to capture the real app object to pass to the thread, 
        # because current_app is a proxy that won't work in the new thread without context.
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

@blueprint.route('/autogen/status', methods=['GET'])
def get_autogen_status():
    """
    Get status of the running or last autogen task.
    """
    import threading
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    
    if not task:
        return success_response(data={'active': False})
    
    # Check if task is technically "running" but thread is gone (server restart/crash)
    if task.status in ['running', 'pending']:
        is_thread_alive = False
        for t in threading.enumerate():
            if t.name == 'autogen_content_thread':
                is_thread_alive = True
                break
        
        if not is_thread_alive:
            # Thread is dead but DB says running -> Stale state
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

@blueprint.route('/autogen/logs', methods=['GET'])
def get_autogen_logs():
    """
    Get activity logs for the current or last autogen task.
    """
    # Get the latest task
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    
    if not task:
        return success_response(data={'logs': []})
    
    # Get logs for this task
    # We use the relationship if available, or query directly
    # Importing BackgroundTaskLog needed
    from mindstack_app.models import BackgroundTaskLog
    
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


@blueprint.route('/redirect-item/<int:item_id>', methods=['GET'])
def redirect_to_item_context(item_id):
    """
    Helper route to find the parent container of an item and redirect to its edit page.
    """
    from mindstack_app.models.learning import LearningItem
    
    item = LearningItem.query.get_or_404(item_id)
    
    if item.item_type in ['QUIZ_MCQ', 'QUIZ_TEXT']:
        return redirect(url_for('content_management.content_management_quizzes.edit_quiz_item', 
                                set_id=item.container_id, item_id=item.item_id))
                                
    elif item.item_type == 'FLASHCARD':
        return redirect(url_for('content_management.content_management_flashcards.edit_flashcard_item', 
                                set_id=item.container_id, item_id=item.item_id))
    
    flash(f"Unknown item type: {item.item_type}", "warning")
    return redirect(url_for('.list_api_keys'))

@blueprint.route('/test_chat', methods=['POST'])
def test_hop_chat():
    """
    Mô tả: Route test nội bộ để thử nghiệm prompt với các model khác nhau.
    """
    try:
        data = request.get_json()
        provider = data.get('provider', 'gemini')
        model = data.get('model', '')
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt không được để trống.'}), 400

        from mindstack_app.modules.AI.services.ai_manager import AIServiceManager
        from mindstack_app.modules.AI.logics.engines.gemini_client import GeminiClient
        from mindstack_app.modules.AI.logics.engines.huggingface_client import HuggingFaceClient
        
        start_time = datetime.now()
        response_text = ""
        
        # Helper to format and send
        if provider == 'gemini':
            client = GeminiClient(model_name=model or 'gemini-2.0-flash-lite-001')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        elif provider == 'huggingface':
            client = HuggingFaceClient(model_name=model or 'google/gemma-7b-it')
            _, response_text = client.generate_content(prompt, feature='test_chat', context_ref='admin_test')
        else: # Hybrid/Default
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

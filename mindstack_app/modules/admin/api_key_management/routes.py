# File: mindstack_app/modules/admin/api_key_management/routes.py
# Phiên bản: 1.0
# Mục đích: Chứa các route và logic cho việc quản lý API keys.

from flask import abort, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from . import api_key_management_bp
from .forms import ApiKeyForm
from ....models import db, ApiKey, BackgroundTask
from ....models.system import SystemSetting, AILog

@api_key_management_bp.before_request
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

@api_key_management_bp.route('/', methods=['GET', 'POST'])
def list_api_keys():
    """
    Mô tả: Dashboard AI Coach - Hiển thị Keys, Settings và Log hoạt động.
    """
    # 1. Fetch API Keys
    keys = ApiKey.query.order_by(ApiKey.key_id.asc()).all()
    
    # 2. Fetch Usage Logs with Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = AILog.query.order_by(desc(AILog.timestamp)).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # 3. Fetch Chart Data (Last 7 Days) - Grouped by Model
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    # Query: Date, Model, Count, Sum(PromptChars), Sum(ResponseChars)
    stats_query = db.session.query(
        func.date(AILog.timestamp).label('date'),
        AILog.model_name,
        func.count(AILog.log_id),
        func.sum(AILog.prompt_chars),
        func.sum(AILog.response_chars)
    ).filter(AILog.timestamp >= seven_days_ago)\
     .group_by('date', AILog.model_name).all()
     
    # Transform data for Chart.js
    dates_set = set()
    models_set = set()
    
    # Maps for different metrics
    # 'YYYY-MM-DD' -> { 'model_a': 10 }
    map_requests = {} 
    # 'YYYY-MM-DD'-> { 'model_a': 5000 }
    map_tokens = {}

    for date_str, model_name, count, sum_prompt, sum_response in stats_query:
        if not date_str or not model_name: continue
        dates_set.add(date_str)
        models_set.add(model_name)
        
        if date_str not in map_requests: map_requests[date_str] = {}
        if date_str not in map_tokens: map_tokens[date_str] = {}
        
        map_requests[date_str][model_name] = count
        # Total chars ~ tokens (rough approx)
        total_chars = (sum_prompt or 0) + (sum_response or 0)
        map_tokens[date_str][model_name] = total_chars
    
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
    def get_setting_value(key, default):
        setting = SystemSetting.query.filter_by(key=key).first()
        if not setting:
            return default
        return setting.value

    current_provider = get_setting_value('AI_PROVIDER', 'gemini')
    gemini_model = get_setting_value('GEMINI_MODEL', 'gemini-1.5-flash')
    hf_model = get_setting_value('HUGGINGFACE_MODEL', 'google/gemma-7b-it')
    
    settings = {
        'provider': current_provider,
        'gemini_model': gemini_model,
        'hf_model': hf_model
    }

    return render_template('api_keys.html', keys=keys, logs=logs, pagination=pagination, ai_settings=settings, chart_data=chart_payload)

@api_key_management_bp.route('/update_settings', methods=['POST'])
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
        def update_or_create(key, value):
            setting = SystemSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = SystemSetting(key=key, value=value, description="AI Coach Setting")
                db.session.add(setting)

        if provider: update_or_create('AI_PROVIDER', provider)
        if gemini_model: update_or_create('GEMINI_MODEL', gemini_model)
        if hf_model: update_or_create('HUGGINGFACE_MODEL', hf_model)

        db.session.commit()
        flash('Đã cập nhật cấu hình AI Coach thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return redirect(url_for('.list_api_keys'))

@api_key_management_bp.route('/add', methods=['GET', 'POST'])
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
    return render_template('add_edit_api_key.html', form=form, title='Thêm API Key mới')

@api_key_management_bp.route('/edit/<int:key_id>', methods=['GET', 'POST'])
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
    return render_template('add_edit_api_key.html', form=form, title='Chỉnh sửa API Key')

@api_key_management_bp.route('/delete/<int:key_id>', methods=['POST'])
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

@api_key_management_bp.route('/autogen/get-sets/<content_type>', methods=['GET'])
def get_sets_for_autogen(content_type):
    """
    Mô tả: Lấy danh sách quiz sets hoặc flashcard sets với thông tin missing content.
    """
    from .autogen_service import get_sets_with_missing_content
    
    result = get_sets_with_missing_content(content_type)
    return jsonify(result)


@api_key_management_bp.route('/autogen/start', methods=['POST'])
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
            return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
        
        # Check for existing task record (Singleton pattern for this task name)
        task = BackgroundTask.query.filter_by(task_name='autogen_content').first()
        
        if task:
            # If exists, check if running
            if task.status == 'running':
                 return jsonify({'success': False, 'message': 'A task is already running', 'task_id': task.task_id}), 409
            
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
        
        return jsonify({'success': True, 'message': 'Task started', 'task_id': task.task_id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_key_management_bp.route('/autogen/status', methods=['GET'])
def get_autogen_status():
    """
    Get status of the running or last autogen task.
    """
    import threading
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    
    if not task:
        return jsonify({'active': False})
    
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
    
    return jsonify({
        'active': True,
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'total': task.total,
        'message': task.message,
        'last_updated': task.last_updated.isoformat() if task.last_updated else None
    })

@api_key_management_bp.route('/autogen/logs', methods=['GET'])
def get_autogen_logs():
    """
    Get activity logs for the current or last autogen task.
    """
    # Get the latest task
    task = BackgroundTask.query.filter_by(task_name='autogen_content').order_by(BackgroundTask.task_id.desc()).first()
    
    if not task:
        return jsonify({'success': False, 'logs': []})
    
    # Get logs for this task
    # We use the relationship if available, or query directly
    # Importing BackgroundTaskLog needed
    from ....models import BackgroundTaskLog
    
    logs = BackgroundTaskLog.query.filter_by(task_id=task.task_id).order_by(BackgroundTaskLog.created_at.asc()).all()
    
    log_data = []
    for log in logs:
        log_data.append({
            'timestamp': log.created_at.isoformat(),
            'message': log.message,
            'status': log.status
        })
        
    return jsonify({'success': True, 'logs': log_data})


@api_key_management_bp.route('/autogen/stop', methods=['POST'])
def stop_autogen():
    """
    Request to stop the running task.
    """
    task = BackgroundTask.query.filter_by(task_name='autogen_content', status='running').first()
    if task:
        task.stop_requested = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Stop requested'})
    return jsonify({'success': False, 'message': 'No running task found'})
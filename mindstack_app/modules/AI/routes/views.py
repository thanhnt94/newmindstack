# File: mindstack_app/modules/AI/routes/views.py
from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, timedelta

from .. import blueprint
from ..models import ApiKey, AiTokenLog
from ..forms import ApiKeyForm
from mindstack_app.models import db, AppSettings

@blueprint.route('/admin/ai/')
@login_required
def dashboard():
    """
    Dashboard AI Coach - Keys, Settings, Logs.
    """
    if current_user.user_role != 'admin':
        abort(403)
        
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

    return render_template('admin/modules/AI/api_keys/api_keys.html', keys=keys, logs=logs, pagination=pagination, ai_settings=settings, chart_data=chart_payload)

@blueprint.route('/admin/ai/keys/add', methods=['GET', 'POST'])
@login_required
def add_key():
    if current_user.user_role != 'admin':
        abort(403)
        
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
    return render_template('admin/modules/AI/api_keys/add_edit_api_key.html', form=form, title='Thêm API Key mới')

@blueprint.route('/admin/ai/keys/edit/<int:key_id>', methods=['GET', 'POST'])
@login_required
def edit_key(key_id):
    if current_user.user_role != 'admin':
        abort(403)
        
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
    return render_template('admin/modules/AI/api_keys/add_edit_api_key.html', form=form, title='Chỉnh sửa API Key')

@blueprint.route('/admin/ai/redirect-item/<int:item_id>', methods=['GET'])
@login_required
def redirect_to_item_context(item_id):
    if current_user.user_role != 'admin':
        abort(403)
        
    from mindstack_app.models import LearningItem
    
    item = LearningItem.query.get_or_404(item_id)
    
    if item.item_type in ['QUIZ_MCQ', 'QUIZ_TEXT']:
        return redirect(url_for('admin.edit_content', container_id=item.container_id)) # Link to admin content edit
                                
    elif item.item_type == 'FLASHCARD':
        return redirect(url_for('admin.edit_content', container_id=item.container_id))
    
    flash(f"Unknown item type: {item.item_type}", "warning")
    return redirect(url_for('.dashboard'))

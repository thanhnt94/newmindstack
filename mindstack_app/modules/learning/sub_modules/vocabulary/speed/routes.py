# File: vocabulary/speed/routes.py
# Speed Review Learning Mode Routes

import json
from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
import random

from . import speed_bp
from mindstack_app.models import LearningContainer, LearningItem, UserContainerState
from ..mcq.logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys

@speed_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """Speed review setup page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items count
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để ôn tập")
    
    # Get available keys for custom pairs
    available_keys = get_available_content_keys(set_id)
    
    # Load saved settings
    saved_settings = {}
    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings:
            saved_settings = ucs.settings.get('speed', {})
    except:
        pass
    
    return render_template(
        'v3/pages/learning/vocabulary/speed/setup/default/index.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys,
        saved_settings=saved_settings
    )

@speed_bp.route('/session/<int:set_id>')
@login_required
def session_page(set_id):
    """Speed review session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get params
    count = request.args.get('count', 10, type=int)
    time_limit = request.args.get('time_limit', 5, type=int)
    lives = request.args.get('lives', 3) # Can be 'inf'
    choices = request.args.get('choices', 4, type=int)
    
    # Custom Pairs
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    # Save settings
    try:
        from mindstack_app.models import db
        from mindstack_app.utils.db_session import safe_commit
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'speed' not in new_settings: new_settings['speed'] = {}
        
        new_settings['speed']['count'] = count
        new_settings['speed']['time_limit'] = time_limit
        new_settings['speed']['lives'] = lives
        if custom_pairs:
            new_settings['speed']['custom_pairs'] = custom_pairs
            
        ucs.settings = new_settings
        safe_commit(db.session)
    except:
        pass
    
    return render_template(
        'v3/pages/learning/vocabulary/speed/session/default/index.html',
        container=container,
        count=count,
        time_limit=time_limit,
        lives=lives,
        custom_pairs=custom_pairs,
        choices=choices
    )

@speed_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for speed review (MCQ format)."""
    count = request.args.get('count', 10, type=int)
    num_choices = request.args.get('choices', 4, type=int)
    
    # Custom pairs
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    mode = 'front_back' # Default
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
            mode = 'custom'
        except:
            pass
            
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        return jsonify({'success': False, 'message': 'Not enough items'}), 400
        
    random.shuffle(items)
    selected_items = items[:min(count, len(items))]
    
    questions = []
    for item in selected_items:
        # Reuse MCQ generator
        q = generate_mcq_question(
            item, items,
            num_choices=num_choices,
            mode=mode,
            custom_pairs=custom_pairs
        )
        questions.append(q)
        
    return jsonify({
        'success': True,
        'questions': questions,
        'total': len(questions)
    })

@speed_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """Check answer (delegates to MCQ check)."""
    data = request.get_json()
    # Speed check is same as MCQ check (index comparison)
    # But we might log 'speed_review' mode specifically in logic if needed.
    # Here we just use the shared function for correctness.
    
    correct_index = data.get('correct_index')
    user_answer_index = data.get('user_answer_index')
    item_id = data.get('item_id')
    user_answer_text = data.get('user_answer_text') # Could be "TIME_OUT"
    duration_ms = data.get('duration_ms', 0)
    
    result = check_mcq_answer(correct_index, user_answer_index)
    result['user_answer'] = user_answer_text
    
    # SRS Update
    if item_id:
        try:
            from mindstack_app.modules.learning.services.srs_service import SrsService
            from mindstack_app.utils.db_session import safe_commit
            from mindstack_app.models import db

            srs_result = SrsService.process_interaction(
                user_id=current_user.user_id,
                item_id=item_id,
                mode='speed_review',
                result_data=result
            )
            safe_commit(db.session)
            result['srs'] = srs_result
        except Exception as e:
            pass
            
    return jsonify(result)

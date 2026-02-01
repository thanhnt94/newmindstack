# File: vocabulary/routes/speed.py
# Speed Review Learning Mode Routes

import json
import random
from flask import render_template, request, jsonify, abort
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import blueprint
from mindstack_app.models import LearningContainer, LearningItem, UserContainerState
from mindstack_app.modules.vocab_mcq.logics.mcq_logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys
from mindstack_app.utils.db_session import safe_commit

@blueprint.route('/speed/setup/<int:set_id>')
@login_required
def speed_setup(set_id):
    """Speed review setup page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để ôn tập")
    
    available_keys = get_available_content_keys(set_id)
    
    saved_settings = {}
    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings:
            saved_settings = ucs.settings.get('speed', {})
    except:
        pass
    
    return render_dynamic_template('modules/learning/vocab_speed/setup/index.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys,
        saved_settings=saved_settings
    )

@blueprint.route('/speed/session/<int:set_id>')
@login_required
def speed_session_page(set_id):
    """Speed review session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    count = request.args.get('count', 10, type=int)
    time_limit = request.args.get('time_limit', 5, type=int)
    lives = request.args.get('lives', 3)
    choices = request.args.get('choices', 4, type=int)
    mode = request.args.get('mode', 'front_back')
    
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    try:
        from mindstack_app.models import db
        
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
        else:
            new_settings['speed']['mode'] = mode
            if 'custom_pairs' in new_settings['speed']:
                del new_settings['speed']['custom_pairs']
            
        ucs.settings = new_settings
        safe_commit(db.session)
    except:
        pass
    
    return render_dynamic_template('modules/learning/vocab_speed/session/index.html',
        container=container,
        count=count,
        time_limit=time_limit,
        lives=lives,
        custom_pairs=custom_pairs,
        choices=choices,
        mode=mode
    )

@blueprint.route('/speed/api/items/<int:set_id>')
@login_required
def speed_api_get_items(set_id):
    """API to get items for speed review (MCQ format)."""
    count = request.args.get('count', 10, type=int)
    num_choices = request.args.get('choices', 4, type=int)
    
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    mode = request.args.get('mode', 'front_back')
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

@blueprint.route('/speed/api/check', methods=['POST'])
@login_required
def speed_api_check_answer():
    """Check answer (delegates to MCQ check)."""
    data = request.get_json()
    
    correct_index = data.get('correct_index')
    user_answer_index = data.get('user_answer_index')
    item_id = data.get('item_id')
    user_answer_text = data.get('user_answer_text')
    duration_ms = data.get('duration_ms', 0)
    
    result = check_mcq_answer(correct_index, user_answer_index)
    result['user_answer'] = user_answer_text
    
    if item_id:
        try:
            from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
            from mindstack_app.models import db

            srs_result = FsrsService.process_interaction(
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

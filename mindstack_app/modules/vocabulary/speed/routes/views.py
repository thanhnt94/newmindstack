# File: vocabulary/routes/speed.py
# Speed Review Learning Mode Routes

import json
import random
from flask import render_template, request, jsonify, abort
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import speed_bp as blueprint
from mindstack_app.models import LearningContainer, LearningItem, UserContainerState, db
from mindstack_app.modules.vocabulary.mcq.interface import (
    get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys
)
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.core.signals import card_reviewed
from mindstack_app.modules.learning_history.interface import LearningHistoryInterface

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
            
            # Map outcome to FSRS Quality (1-4)
            fsrs_quality = 3 if result['is_correct'] else 1
            score_change = 10 if result['is_correct'] else 0
            result['score_change'] = score_change

            srs_result = FsrsService.process_interaction(
                user_id=current_user.user_id,
                item_id=item_id,
                quality=fsrs_quality,
                mode='speed_review',
                result_data=result
            )
            
            # [EMIT] Signal
            try:
                item = LearningItem.query.get(item_id)
                item_type = item.item_type if item else 'FLASHCARD'
                card_reviewed.send(
                    None,
                    user_id=current_user.user_id,
                    item_id=item_id,
                    quality=fsrs_quality,
                    is_correct=result['is_correct'],
                    learning_mode='speed_review',
                    score_points=score_change,
                    item_type=item_type,
                    reason=f"Vocab Speed Review {'Correct' if result['is_correct'] else 'Incorrect'}"
                )
            except: pass
            
            # [LOG] History
            try:
                fsrs_snapshot = {
                    'stability': srs_result.get('stability'),
                    'difficulty': srs_result.get('difficulty'),
                    'state': srs_result.get('state'),
                    'next_review': srs_result.get('next_review').isoformat() if srs_result.get('next_review') and hasattr(srs_result.get('next_review'), 'isoformat') else srs_result.get('next_review')
                }
                LearningHistoryInterface.record_log(
                    user_id=current_user.user_id,
                    item_id=item_id,
                    result_data={
                        'rating': fsrs_quality,
                        'user_answer': user_answer_text,
                        'is_correct': result['is_correct'],
                        'review_duration': duration_ms
                    },
                    context_data={
                        'learning_mode': 'speed_review'
                    },
                    fsrs_snapshot=fsrs_snapshot,
                    game_snapshot={'score_earned': score_change}
                )
            except: pass

            safe_commit(db.session)
            result['srs'] = srs_result
            result['updated_total_score'] = current_user.total_score
        except Exception as e:
            import traceback
            traceback.print_exc()
            
    return jsonify(result)

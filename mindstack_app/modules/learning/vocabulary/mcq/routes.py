# File: vocabulary/mcq/routes.py
# MCQ (Multiple Choice Quiz) Routes for Vocabulary Learning

import json
from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import mcq_bp
from .logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys
from mindstack_app.models import LearningContainer


@mcq_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """MCQ setup page - choose mode, columns, number of questions."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items count
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để chơi trắc nghiệm")
    
    # Get available content keys for custom column selection
    available_keys = get_available_content_keys(set_id)
    
    return render_template(
        'mcq/setup.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys
    )


@mcq_bp.route('/api/keys/<int:set_id>')
@login_required
def api_get_keys(set_id):
    """API to get available content keys for a set."""
    keys = get_available_content_keys(set_id)
    return jsonify({
        'success': True,
        'keys': keys
    })


@mcq_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """MCQ learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để chơi trắc nghiệm")
    
    # Get params from query
    mode = request.args.get('mode', 'front_back')
    count = request.args.get('count', 10, type=int)
    choices = request.args.get('choices', 4, type=int)
    
    # Get custom_pairs if provided
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass
    
    return render_template(
        'mcq/session.html',
        container=container,
        total_items=len(items),
        mode=mode,
        count=count,
        choices=choices,
        custom_pairs=custom_pairs
    )


@mcq_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get MCQ items for a session."""
    count = request.args.get('count', 10, type=int)
    mode = request.args.get('mode', 'front_back')
    num_choices = request.args.get('choices', 4, type=int)
    
    # Get custom_pairs if provided
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass
    
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        return jsonify({'success': False, 'message': 'Cần ít nhất 2 thẻ để chơi trắc nghiệm'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected_items = items[:min(count, len(items))]
    
    # Generate questions for each selected item
    questions = []
    for item in selected_items:
        question = generate_mcq_question(
            item, items, 
            num_choices=num_choices, 
            mode=mode,
            custom_pairs=custom_pairs
        )
        questions.append(question)
    
    return jsonify({
        'success': True,
        'questions': questions,
        'total': len(questions)
    })


@mcq_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API to check MCQ answer."""
    data = request.get_json()
    correct_index = data.get('correct_index')
    user_answer_index = data.get('user_answer_index')
    item_id = data.get('item_id')
    
    if correct_index is None or user_answer_index is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    result = check_mcq_answer(correct_index, user_answer_index)
    
    # Update SRS if item_id provided
    if item_id:
        try:
            from mindstack_app.modules.learning.vocabulary.services.srs_service import VocabularySrsService
            from mindstack_app.modules.shared.utils.db_session import safe_commit
            from mindstack_app.models import db

            srs_result = VocabularySrsService.process_interaction(
                user_id=current_user.user_id,
                item_id=item_id,
                mode='mcq',
                result_data=result
            )
            safe_commit(db.session)
            result['srs'] = srs_result
        except Exception as e:
            # Log but don't fail
            import logging
            logging.warning(f"SRS update failed for MCQ: {e}")
    
    result['success'] = True
    return jsonify(result)

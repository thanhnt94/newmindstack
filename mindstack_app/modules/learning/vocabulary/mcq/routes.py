# File: vocabulary/mcq/routes.py
# MCQ Learning Mode Routes

from flask import render_template, request, jsonify, abort
import json
from flask_login import login_required, current_user

from . import mcq_bp
from .logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys
from mindstack_app.models import LearningContainer


@mcq_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """MCQ learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    mode = request.args.get('mode', 'front_back')
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items
    items = get_mcq_eligible_items(set_id)
    if len(items) < 4:
        abort(400, description="Cần ít nhất 4 thẻ để chơi trắc nghiệm")
    
    return render_template(
        'mcq/session/index.html',
        container=container,
        total_items=len(items),
        mode=mode
    )


@mcq_bp.route('/get_mcq_options_partial/<int:set_id>')
@login_required
def get_mcq_options_partial(set_id):
    """Render the MCQ options selection partial."""
    container = LearningContainer.query.get_or_404(set_id)
    items = get_mcq_eligible_items(set_id)
    available_columns = get_available_content_keys(set_id)
    return render_template('mcq/setup/_options_list.html',
                          container=container,
                          total_items=len(items),
                          available_columns=available_columns)


@mcq_bp.route('/api/questions/<int:set_id>')
@login_required
def api_get_questions(set_id):
    """API to get MCQ questions for a session."""
    count = request.args.get('count', 10, type=int)
    mode = request.args.get('mode', 'front_back')
    question_key = request.args.get('question_column')
    answer_key = request.args.get('answer_column')
    
    custom_pairs_str = request.args.get('custom_pairs')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass
    
    answer_count = int(request.args.get('answer_count', 4))
    if answer_count < 2:
        answer_count = 2
    if answer_count > 8:
        answer_count = 8
    
    items = get_mcq_eligible_items(set_id)
    if len(items) < answer_count:
        return jsonify({'success': False, 'message': 'Not enough items'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected = items[:min(count, len(items))]
    
    # Generate questions
    questions = []
    for item in selected:
        q = generate_mcq_question(item, items, mode=mode, question_key=question_key, answer_key=answer_key, custom_pairs=custom_pairs, num_choices=answer_count)
        questions.append(q)
    
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
    item_id = data.get('item_id')
    user_answer = data.get('answer', '')
    answer_key = data.get('answer_column')
    
    result = check_mcq_answer(item_id, user_answer, user_id=current_user.user_id, answer_key=answer_key)
    return jsonify(result)


@mcq_bp.route('/api/item/<int:item_id>')
@login_required
def api_get_item(item_id):
    """API to get item details for the info modal."""
    from mindstack_app.models import LearningItem
    
    item = LearningItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404
    
    # Check access to the container
    container = item.container
    if not container:
        return jsonify({'success': False, 'message': 'Container not found'}), 404
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    return jsonify({
        'success': True,
        'item': {
            'item_id': item.item_id,
            'content': item.content or {}
        }
    })

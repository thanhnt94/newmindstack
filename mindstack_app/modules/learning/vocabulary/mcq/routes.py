# File: vocabulary/mcq/routes.py
# MCQ Learning Mode Routes

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import mcq_bp
from .logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer
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
        'mcq/session.html',
        container=container,
        total_items=len(items),
        mode=mode
    )


@mcq_bp.route('/get_mcq_options_partial/<int:set_id>')
@login_required
def get_mcq_options_partial(set_id):
    """Render the MCQ options selection partial."""
    return render_template('vocabulary/mcq/setup/_options_list.html')


@mcq_bp.route('/api/questions/<int:set_id>')
@login_required
def api_get_questions(set_id):
    """API to get MCQ questions for a session."""
    count = request.args.get('count', 10, type=int)
    mode = request.args.get('mode', 'front_back')
    
    items = get_mcq_eligible_items(set_id)
    if len(items) < 4:
        return jsonify({'success': False, 'message': 'Not enough items'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected = items[:min(count, len(items))]
    
    # Generate questions
    questions = []
    for item in selected:
        q = generate_mcq_question(item, items, mode=mode)
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
    
    result = check_mcq_answer(item_id, user_answer, user_id=current_user.user_id)
    return jsonify(result)

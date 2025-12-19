# File: vocabulary/typing/routes.py
# Typing Learning Mode Routes

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import typing_bp
from .logic import get_typing_eligible_items, check_typing_answer
from mindstack_app.models import LearningContainer


@typing_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """Typing learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items
    items = get_typing_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi gõ đáp án")
    
    return render_template(
        'typing/session.html',
        container=container,
        total_items=len(items)
    )


@typing_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for a typing session."""
    count = request.args.get('count', 10, type=int)
    
    items = get_typing_eligible_items(set_id)
    if len(items) < 1:
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected = items[:min(count, len(items))]
    
    return jsonify({
        'success': True,
        'items': selected,
        'total': len(selected)
    })


@typing_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API to check typed answer."""
    data = request.get_json()
    correct_answer = data.get('correct_answer', '')
    user_answer = data.get('user_answer', '')
    
    result = check_typing_answer(correct_answer, user_answer)
    return jsonify(result)

# File: vocabulary/typing/routes.py
# Typing Learning Mode Routes

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import typing_bp
from .logic import get_typing_eligible_items, check_typing_answer
from ..mcq.logic import get_available_content_keys  # Reuse from MCQ
from mindstack_app.models import LearningContainer


@typing_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """Typing setup page - choose columns."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_typing_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi gõ đáp án")
    
    available_keys = get_available_content_keys(set_id)
    
    return render_template(
        'typing/setup.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys
    )


@typing_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """Typing learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get custom_pairs if provided
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            import json
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    # Get eligible items
    items = get_typing_eligible_items(set_id, custom_pairs=custom_pairs)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi gõ đáp án")
    
    return render_template(
        'typing/session.html',
        container=container,
        total_items=len(items),
        custom_pairs=custom_pairs
    )


@typing_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for a typing session."""
    count = request.args.get('count', 10, type=int)
    
    # Get custom_pairs if provided
    custom_pairs_str = request.args.get('custom_pairs', '')
    custom_pairs = None
    if custom_pairs_str:
        try:
            import json
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    items = get_typing_eligible_items(set_id, custom_pairs=custom_pairs)
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
    
    # Update SRS
    item_id = data.get('item_id')
    if item_id:
        from mindstack_app.modules.learning.vocabulary.services.srs_service import VocabularySrsService
        from mindstack_app.modules.shared.utils.db_session import safe_commit
        from mindstack_app.models import db

        srs_result = VocabularySrsService.process_interaction(
            user_id=current_user.user_id,
            item_id=item_id,
            mode='typing',
            result_data=result
        )
        safe_commit(db.session)
        result['srs'] = srs_result

    return jsonify(result)

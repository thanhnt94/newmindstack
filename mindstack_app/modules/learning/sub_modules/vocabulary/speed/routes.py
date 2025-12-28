# File: vocabulary/speed/routes.py
# Speed Review Learning Mode Routes

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
import random

from . import speed_bp
from mindstack_app.models import LearningContainer, LearningItem


@speed_bp.route('/session/<int:set_id>')
@login_required
def session_page(set_id):
    """Speed review session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get items
    items = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='FLASHCARD'
    ).all()
    
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để ôn tập")
    
    # Prepare items data
    cards = []
    for item in items:
        content = item.content or {}
        if content.get('front') and content.get('back'):
            cards.append({
                'item_id': item.item_id,
                'front': content.get('front'),
                'back': content.get('back'),
            })
    
    random.shuffle(cards)
    
    return render_template(
        'speed/session/default/index.html',
        container=container,
        cards=cards,
        total=len(cards)
    )


@speed_bp.route('/api/log_session', methods=['POST'])
@login_required
def log_session():
    """Bulk log speed review session results."""
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'success': False, 'message': 'No items to log'}), 400
        
    from mindstack_app.modules.learning.core.services.srs_service import SrsService
    from mindstack_app.modules.shared.utils.db_session import safe_commit
    from mindstack_app.models import db
    
    results = []
    
    for item in items:
        item_id = item.get('item_id')
        is_correct = item.get('is_correct')
        duration_ms = item.get('duration_ms', 0)
        user_answer = item.get('user_answer') # e.g. "Known" or "Forgotten"
        
        if item_id is not None and is_correct is not None:
            res = SrsService.process_interaction(
                user_id=current_user.user_id,
                item_id=item_id,
                mode='speed_review',
                result_data={
                    'is_correct': is_correct,
                    'duration_ms': duration_ms,
                    'user_answer': user_answer
                }
            )
            results.append(res)
            
    safe_commit(db.session)
    
    return jsonify({
        'success': True,
        'count': len(results)
    })

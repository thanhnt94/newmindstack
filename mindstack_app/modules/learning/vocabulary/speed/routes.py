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
        'speed/session.html',
        container=container,
        cards=cards,
        total=len(cards)
    )

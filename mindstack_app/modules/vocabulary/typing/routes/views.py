from flask import render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningSession, LearningItem, db
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
from .. import typing_bp as blueprint
from ..logics.typing_logic import get_typing_items
from datetime import datetime, timezone

@blueprint.route('/')
@login_required
def typing_dashboard():
    """Dashboard cho chế độ gõ từ."""
    # Lấy các bộ thẻ
    containers = LearningContainer.query.filter_by(
        container_type='FLASHCARD_SET',
        creator_user_id=current_user.user_id
    ).all()
    
    return render_dynamic_template('modules/learning/vocab_typing/dashboard.html', containers=containers)

@blueprint.route('/setup/<int:set_id>')
@login_required
def typing_setup(set_id):
    """Bắt đầu luôn phiên gõ từ cho bộ thẻ (Bypass setup screen)."""
    return redirect(url_for('vocab_typing.typing_session_page', set_id=set_id))

@blueprint.route('/session')
@blueprint.route('/session/<int:set_id>')
@login_required
def typing_session_page(set_id=None):
    """Trang phiên học gõ từ."""
    container = None
    if set_id:
        container = LearningContainer.query.get_or_404(set_id)
    
    # REFAC: Use FSRSInterface to get stats
    stats = FsrsInterface.get_memory_stats_by_type(current_user.user_id, 'FLASHCARD')
    
    count_review = stats.get('due', 0)
    count_learned = stats.get('total', 0) - stats.get('new', 0)
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        container=container,
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )

@blueprint.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API lấy danh sách từ cho phiên học gõ."""
    count = request.args.get('count', 10, type=int)
    items = get_typing_items(current_user.user_id, container_id=set_id, limit=count)
    
    # Format items for UI
    formatted_items = []
    for item in items:
        formatted_items.append({
            'item_id': item.item_id,
            'prompt': item.front or item.content.get('front', ''),
            'answer': item.back or item.content.get('back', '')
        })
    
    return jsonify({
        'success': True,
        'items': formatted_items
    })

@blueprint.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API kiểm tra đáp án và cập nhật SRS."""
    data = request.get_json()
    item_id = data.get('item_id')
    user_answer = data.get('user_answer', '').strip()
    duration_ms = data.get('duration_ms', 0)
    
    if not item_id:
        return jsonify({'success': False, 'message': 'Missing item_id'}), 400
        
    item = LearningItem.query.get_or_404(item_id)
    correct_answer = (item.back or item.content.get('back', '')).strip()
    
    is_correct = user_answer.lower() == correct_answer.lower()
    quality = 5 if is_correct else 0
    
    # Process interaction via FSRS
    result = FsrsInterface.process_interaction(
        user_id=current_user.user_id,
        item_id=item_id,
        mode='typing',
        result_data={
            'quality': quality,
            'duration_ms': duration_ms,
            'user_answer': user_answer,
            'timestamp': datetime.now(timezone.utc)
        }
    )
    
    # Safe commit is usually handled inside process_interaction or via after_request
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'srs': result
    })

@blueprint.route('/api/end_session', methods=['POST'])
@login_required
def api_end_session():
    """Kết thúc phiên học."""
    # Logic kết thúc phiên học có thể thêm vào đây (như đánh dấu session hoàn thành trong DB)
    return jsonify({'success': True})
from flask import render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningItem, db
from mindstack_app.core.signals import card_reviewed
from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
from mindstack_app.utils.bbcode_parser import bbcode_to_html
# REFAC: Remove ItemMemoryState
from .. import listening_bp as blueprint
from ..logics.listening_logic import get_listening_items
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
import random
from datetime import datetime, timezone

@blueprint.route('/')
@login_required
def listening_dashboard():
    """Dashboard cho chế độ luyện nghe."""
    # Lấy các bộ thẻ có thể học
    containers = LearningContainer.query.filter_by(
        container_type='FLASHCARD_SET',
        creator_user_id=current_user.user_id # Tạm thời chỉ lấy của chính mình
    ).all()
    
    return render_dynamic_template('modules/learning/vocab_listening/dashboard.html', containers=containers)

@blueprint.route('/setup/<int:set_id>')
@login_required
def listening_setup(set_id):
    """Bắt đầu luôn phiên luyện nghe cho bộ thẻ (Bypass setup screen)."""
    return redirect(url_for('vocab_listening.listening_session_page', set_id=set_id))

@blueprint.route('/session')
@blueprint.route('/session/<int:set_id>')
@login_required
def listening_session_page(set_id=None):
    """Trang phiên học luyện nghe."""
    container = None
    if set_id:
        container = LearningContainer.query.get_or_404(set_id)
        
    # Logic thống kê sơ bộ để hiển thị (số lượng thẻ cần ôn)
    # REFAC: Use FsrsInterface to retrieve stats
    stats = FsrsInterface.get_memory_stats_by_type(current_user.user_id, 'FLASHCARD')
    
    count_review = stats.get('due', 0)
    # learned = total - new (includes reviewing, learning, mastered) or just use 'total' - 'new'
    count_learned = stats.get('total', 0) - stats.get('new', 0)
    
    return render_dynamic_template('modules/learning/vocab_listening/session/index.html',
        container=container,
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )

@blueprint.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API lấy danh sách từ cho phiên học nghe."""
    count = request.args.get('count', 10, type=int)
    # TODO: Update get_listening_items to support container_id
    items = get_listening_items(current_user.user_id, limit=count)
    
    # Format items for UI
    formatted_items = []
    for item in items:
        # Listening specific format
        formatted_items.append({
            'item_id': item.item_id,
            'audio_url': item.content.get('front_audio_url') or item.content.get('back_audio_url') or '',
            'audio_content': item.content.get('front_audio_content') or item.content.get('back_audio_content') or '',
            'answer': bbcode_to_html(item.back or item.content.get('back', '')),
            'prompt': bbcode_to_html(item.front or item.content.get('front', '')) # Optional hint
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
    # Map to FSRS Quality (1-4) for consistent logging
    fsrs_quality = 3 if is_correct else 1
    score_change = 10 if is_correct else 0
    
    # [REMOVED] FSRS update as requested
    
    # [EMIT] Signal for gamification
    try:
        card_reviewed.send(
            None,
            user_id=current_user.user_id,
            item_id=item_id,
            quality=fsrs_quality,
            is_correct=is_correct,
            learning_mode='listening',
            score_points=score_change,
            item_type=item.item_type or 'FLASHCARD',
            reason=f"Vocab Listening Practice {'Correct' if is_correct else 'Incorrect'}"
        )
    except: pass
    
    # [LOG] History
    try:
        LearningHistoryInterface.record_log(
            user_id=current_user.user_id,
            item_id=item_id,
            result_data={
                'rating': fsrs_quality,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'review_duration': duration_ms
            },
            context_data={
                'learning_mode': 'listening'
            },
            game_snapshot={'score_earned': score_change}
        )
    except: pass

    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'updated_total_score': current_user.total_score
    })

@blueprint.route('/api/end_session', methods=['POST'])
@login_required
def api_end_session():
    """Kết thúc phiên học."""
    return jsonify({'success': True})
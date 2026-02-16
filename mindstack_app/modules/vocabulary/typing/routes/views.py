from flask import render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningSession, LearningItem, db
from mindstack_app.utils.bbcode_parser import bbcode_to_html
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
from mindstack_app.modules.gamification.interface import award_points
from mindstack_app.modules.session.interface import SessionInterface
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
    
    # Find active session
    active_session = SessionInterface.get_active_session(current_user.user_id, learning_mode='typing', set_id_data=set_id)
    session_id = active_session.session_id if active_session else None
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        container=container,
        session_id=session_id,
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )

@blueprint.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API lấy danh sách từ cho phiên học gõ (có kèm thông số FSRS)."""
    count = request.args.get('count', type=int) # Default to None (All items)
    
    # Check for existing session
    active_session = SessionInterface.get_active_session(current_user.user_id, learning_mode='typing', set_id_data=set_id)
    
    # Auto-restart if user requests Unlimited (count=None) but active session is limited (e.g. 10 items)
    # This fixes the "1/10" persistence issue.
    if active_session and count is None:
        if active_session.total_items == 10: # Legacy default limit
             # Check if user has made significant progress. If not (or if we want to force), restart.
             # Here we just force restart to ensure they get the full list as requested.
             SessionInterface.complete_session(active_session.session_id)
             active_session = None

    if active_session:
        # Resume session
        item_ids = active_session.session_data.get('item_ids', [])
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        # Sort items to match original order
        item_map = {item.item_id: item for item in items}
        items = [item_map[iid] for iid in item_ids if iid in item_map]
        
        processed_ids = active_session.processed_item_ids or []
        correct_count = active_session.correct_count or 0
        incorrect_count = active_session.incorrect_count or 0
        points_earned = active_session.points_earned or 0
        
        session_data = active_session.session_data or {}
        current_index = session_data.get('current_index', len(processed_ids))
        is_showing_answer = session_data.get('is_showing_answer', False)
        last_user_answer = session_data.get('last_user_answer', '')
    else:
        # Start new session
        # mode='all' ensures we get both New and Reviewed items (fixing 0 stats issue)
        items = get_typing_items(current_user.user_id, container_id=set_id, limit=count, mode='all')
        item_ids = [item.item_id for item in items]
        
        # Create DB session for persistence
        active_session = SessionInterface.create_session(
            user_id=current_user.user_id,
            learning_mode='typing',
            mode_config_id='typing',
            set_id_data=set_id,
            total_items=len(item_ids)
        )
        if active_session:
            active_session.session_data = {
                'item_ids': item_ids,
                'current_index': 0,
                'is_showing_answer': False
            }
            db.session.commit()
            
        processed_ids = []
        correct_count = 0
        incorrect_count = 0
        points_earned = 0
        current_index = 0
        is_showing_answer = False
        last_user_answer = ''
    
    # Fetch FSRS stats for all items in batch
    fsrs_states = FsrsInterface.get_batch_memory_states(current_user.user_id, item_ids)
    
    # Format items for UI
    formatted_items = []
    for item in items:
        content = item.content if item.content else {}
        prompt_raw = getattr(item, 'front', content.get('front', ''))
        answer_raw = getattr(item, 'back', content.get('back', ''))
        
        # FSRS stats
        state = fsrs_states.get(item.item_id)
        fsrs_info = {
            'stability': round(state.stability, 2) if state and state.stability else 0,
            'difficulty': round(state.difficulty, 2) if state and state.difficulty else 0,
            'retrievability': round(FsrsInterface.calculate_retrievability_for_record(state) * 100, 1),
            'last_review': state.last_review.isoformat() if state and state.last_review else None
        }
        
        formatted_items.append({
            'item_id': item.item_id,
            'prompt': bbcode_to_html(prompt_raw),
            'answer': bbcode_to_html(answer_raw),
            'fsrs': fsrs_info
        })
    
    return jsonify({
        'success': True,
        'items': formatted_items,
        'session_id': active_session.session_id if active_session else None,
        'progress': {
            'processed_item_ids': processed_ids,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'points_earned': points_earned,
            'current_index': current_index,
            'is_showing_answer': is_showing_answer,
            'last_user_answer': last_user_answer
        }
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
    content = item.content if item.content else {}
    from mindstack_app.utils.content_renderer import strip_bbcode
    correct_answer = strip_bbcode(getattr(item, 'back', content.get('back', ''))).strip()
    
    is_correct = user_answer.lower() == correct_answer.lower()
    
    # Map correctness to FSRS quality (Rating enum)
    quality = FsrsInterface.Rating.Good if is_correct else FsrsInterface.Rating.Again
    
    # Process interaction via FSRS
    memory_state, srs_result = FsrsInterface.process_review(
        user_id=current_user.user_id,
        item_id=item_id,
        quality=quality,
        mode='typing',
        duration_ms=duration_ms,
        container_id=item.container_id
    )
    
    # Award points via ScoreService
    score_change = 0
    if is_correct:
        score_info = award_points(
            user_id=current_user.user_id,
            amount=10,
            reason="Gõ từ chính xác",
            item_id=item_id,
            item_type='FLASHCARD'
        )
        score_change = score_info.get('score_change', 10)
    
    # Sync with LearningSession
    active_session = SessionInterface.get_active_session(current_user.user_id, learning_mode='typing', set_id_data=item.container_id)
    if active_session:
        SessionInterface.update_progress(
            session_id=active_session.session_id,
            item_id=item_id,
            result_type='correct' if is_correct else 'incorrect',
            points=score_change
        )
        # Store state for reload
        session_data = dict(active_session.session_data or {})
        session_data['is_showing_answer'] = True
        session_data['last_user_answer'] = user_answer
        active_session.session_data = session_data
        db.session.add(active_session)
    
    db.session.commit()
    
    srs_data = {
        'score_change': score_change,
        'stability': round(srs_result.stability, 2),
        'difficulty': round(srs_result.difficulty, 2),
        'retrievability': round(srs_result.retrievability * 100, 1),
        'next_review': srs_result.next_review.isoformat(),
        'interval_minutes': srs_result.interval_minutes
    }
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'srs': srs_data
    })

@blueprint.route('/api/next', methods=['POST'])
@login_required
def api_next_item():
    """API chuyển sang câu tiếp theo (sync session index)."""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id:
        active = SessionInterface.get_active_session(current_user.user_id, learning_mode='typing')
        if active: session_id = active.session_id
        
    if not session_id:
        return jsonify({'success': False, 'message': 'No active session'}), 404
        
    session = db.session.get(LearningSession, session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Session not found'}), 404
        
    session_data = dict(session.session_data or {})
    current_index = session_data.get('current_index', 0)
    item_ids = session_data.get('item_ids', [])
    
    # [NEW] Check for End of Cycle (Unlimited Mode)
    # If we are about to move past the last item
    if current_index >= len(item_ids) - 1:
        # Check if unlimited (assuming count was not set or we just want infinite loop)
        # We can just always loop in this mode as requested by user ("all unlimited")
        import random
        random.shuffle(item_ids)
        session_data['item_ids'] = item_ids
        session_data['current_index'] = 0
        session_data['is_showing_answer'] = False
        session_data['last_user_answer'] = ''
        
        session.session_data = session_data
        db.session.add(session)
        db.session.commit()
        
        # Fetch new items to return
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        # Sort items to match new order
        item_map = {item.item_id: item for item in items}
        formatted_items = []
        for iid in item_ids:
            if iid in item_map:
                item = item_map[iid]
                # Re-serialize item if needed, or use a helper
                # Using ad-hoc serialization matching api_get_items logic (simplified)
                content = item.content if item.content else {}
                from mindstack_app.utils.content_renderer import strip_bbcode, bbcode_to_html_simple
                prompt = bbcode_to_html_simple(getattr(item, 'front', content.get('front', '')))
                
                # Get FSRS stats
                fsrs_state = None
                from mindstack_app.models import ItemMemoryState
                params = getattr(item, 'fsrs_memory_state', None)
                if params and isinstance(params, dict):
                    fsrs_state = params
                
                formatted_items.append({
                    'item_id': item.item_id,
                    'prompt': prompt,
                    'answer': strip_bbcode(getattr(item, 'back', content.get('back', ''))),
                    # Simplified fsrs for re-fetch
                    'fsrs': fsrs_state or {'stability':0, 'difficulty':0, 'retrievability':0}
                })

        return jsonify({
            'success': True,
            'new_cycle': True,
            'items': formatted_items,
            'next_index': 0
        })

    # Normal progression
    session_data['current_index'] = current_index + 1
    session_data['is_showing_answer'] = False
    session_data['last_user_answer'] = ''
    
    session.session_data = session_data
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'next_index': current_index + 1
    })

@blueprint.route('/api/end_session', methods=['POST'])
@login_required
def api_end_session():
    """Kết thúc phiên học."""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id:
        active = SessionInterface.get_active_session(current_user.user_id, learning_mode='typing')
        if active:
            session_id = active.session_id
            
    if session_id:
        SessionInterface.complete_session(session_id)
        return jsonify({'success': True, 'session_id': session_id})
        
    return jsonify({'success': False, 'message': 'No active session found'})

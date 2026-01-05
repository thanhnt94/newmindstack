# File: vocabulary/typing/routes.py
# Typing Learning Mode Routes

from flask import render_template, request, jsonify, abort, url_for
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
    
    # Calculate counts for each mode
    from mindstack_app.models import LearningItem, LearningProgress
    from datetime import datetime, timezone

    base_query = LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD')
    
    # New
    count_new = base_query.filter(~LearningItem.progress_records.any()).count()
    
    # Review
    now = datetime.now(timezone.utc)
    count_review = base_query.join(LearningProgress).filter(LearningProgress.due_time <= now).count()
    
    # Learned (Review All)
    count_learned = base_query.join(LearningProgress).count()
    
    # Hard (Simplified: easiness_factor < 2.5)
    count_hard = base_query.join(LearningProgress).filter(LearningProgress.easiness_factor < 2.5).count()
    
    # Random
    count_random = len(items)

    # [UPDATED] Load saved settings & defaults
    saved_settings = {}
    default_settings = {}
    
    # 1. defaults
    if container.settings and container.settings.get('typing'):
        default_settings = container.settings.get('typing').copy()
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    # 2. saved user state
    try:
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('typing'):
            saved_settings = ucs.settings.get('typing', {})
    except Exception as e:
        pass

    return render_template(
        'v3/pages/learning/vocabulary/typing/setup/index.html',
        container=container,
        counts={
            'new': count_new,
            'review': count_review,
            'learned': count_learned,
            'hard': count_hard,
            'random': count_random
        },
        total_items=len(items),
        available_keys=available_keys,
        saved_settings=saved_settings,
        default_settings=default_settings
    )


@typing_bp.route('/start', methods=['POST'])
@login_required
def start_session():
    """Start a typing session: Save settings and redirect."""
    try:
        from flask import session
        data = request.get_json()
        
        set_id = data.get('set_id')
        mode = data.get('mode', 'custom')
        count = data.get('count', 10)
        custom_pairs = data.get('custom_pairs')
        
        if not set_id:
            return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        # Save to Session
        session['typing_session'] = {
            'set_id': set_id,
            'mode': mode,
            'count': count,
            'custom_pairs': custom_pairs
        }
        
        # Save preferences to DB (UserContainerState)
        try:
            from mindstack_app.models import UserContainerState, db
            from mindstack_app.utils.db_session import safe_commit
            
            ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
                db.session.add(ucs)
            
            new_settings = dict(ucs.settings or {})
            if 'typing' not in new_settings: new_settings['typing'] = {}
            new_settings['typing']['count'] = count
            if custom_pairs:
                new_settings['typing']['custom_pairs'] = custom_pairs
            
            ucs.settings = new_settings
            safe_commit(db.session)
        except Exception as e:
            import traceback
            traceback.print_exc()
            
        return jsonify({
            'success': True, 
            'redirect_url': url_for('learning.vocabulary.typing.session_page')
        })
    except Exception as outer_e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f"Server Error: {str(outer_e)}"}), 500


@typing_bp.route('/session/')
@login_required
def session_page():
    """Typing learning session page (Clean URL)."""
    from flask import session
    
    session_data = session.get('typing_session', {})
    set_id = session_data.get('set_id')
    
    if not set_id:
        # Fallback or redirect to dashboard
        return redirect(url_for('learning.vocabulary.dashboard'))
        
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    # Get params (Already in session, but we might pass to template if needed)
    custom_pairs = session_data.get('custom_pairs')
    count = session_data.get('count', 10)
    
    return render_template(
        'v3/pages/learning/vocabulary/typing/session/index.html',
        container=container,
        custom_pairs=custom_pairs,
        count=count
    )


@typing_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for a typing session."""
    from flask import session
    
    # Priority: URL Args (for testing/link sharing) > Session > Defaults
    count = request.args.get('count', type=int)
    custom_pairs_str = request.args.get('custom_pairs', '')
    
    custom_pairs = None
    
    # Try getting from session if set_id matches
    session_data = session.get('typing_session', {})
    if session_data.get('set_id') == set_id:
        if not count: count = session_data.get('count')
        if not custom_pairs_str and session_data.get('custom_pairs'):
            custom_pairs = session_data.get('custom_pairs')

    # Fallback default
    if not count: count = 10
    
    # Parse URL custom_pairs if exists (overrides session)
    if custom_pairs_str:
        try:
            import json
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    # Get Mode
    mode = session_data.get('mode', 'custom')

    items = get_typing_eligible_items(set_id, custom_pairs=custom_pairs, mode=mode)
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
    duration_ms = data.get('duration_ms', 0)
    
    result = check_typing_answer(correct_answer, user_answer)
    result['user_answer'] = user_answer
    result['duration_ms'] = duration_ms
    
    # Update SRS
    item_id = data.get('item_id')
    if item_id:
        from mindstack_app.modules.learning.services.srs_service import SrsService
        from mindstack_app.utils.db_session import safe_commit
        from mindstack_app.models import db

        srs_result = SrsService.process_interaction(
            user_id=current_user.user_id,
            item_id=item_id,
            mode='typing',
            result_data=result
        )
        safe_commit(db.session)
        result['srs'] = srs_result

    return jsonify(result)

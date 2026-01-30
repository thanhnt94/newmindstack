# File: vocabulary/typing/routes.py
# Typing Learning Mode Routes

from flask import render_template, request, jsonify, abort, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
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
    count_review = base_query.join(LearningProgress).filter(LearningProgress.fsrs_due <= now).count()
    
    # Learned (Review All)
    count_learned = base_query.join(LearningProgress).count()
    
    # Hard - Use centralized HardItemService
    from mindstack_app.modules.learning.services.hard_item_service import HardItemService
    count_hard = HardItemService.get_hard_count(current_user.user_id, set_id)
    
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

    return render_dynamic_template('pages/learning/vocabulary/typing/setup/index.html',
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
        from mindstack_app.modules.flashcard.services.session_service import LearningSessionService
        
        data = request.get_json()
        
        set_id = data.get('set_id')
        mode = data.get('mode', 'custom')
        count = data.get('count', 10)
        use_custom_config = data.get('use_custom_config', False)
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
        
        # Create DB Session
        try:
            db_session = LearningSessionService.create_session(
                user_id=current_user.user_id,
                learning_mode='typing',
                mode_config_id=mode,
                set_id_data=set_id,
                total_items=count if count else 0
            )
            if db_session:
                session['typing_session']['db_session_id'] = db_session.session_id
        except Exception as e:
            print(f"Error creating DB session for typing: {e}")

        # Save preferences to DB (UserContainerState)
        try:
            from mindstack_app.models import UserContainerState, db
            from mindstack_app.utils.db_session import safe_commit
            from sqlalchemy.orm.attributes import flag_modified
            
            ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
                db.session.add(ucs)
            
            new_settings = dict(ucs.settings or {})
            if 'typing' not in new_settings: new_settings['typing'] = {}
            
            new_settings['typing']['mode'] = mode
            # Allow count=0 for unlimited. Only default to 10 if count is None.
            if count is not None:
                new_settings['typing']['count'] = int(count)
            else:
                new_settings['typing']['count'] = 10
            new_settings['typing']['use_custom_config'] = bool(use_custom_config)
            if custom_pairs:
                new_settings['typing']['custom_pairs'] = custom_pairs
            
            ucs.settings = new_settings
            
            # CRITICAL: Trigger SQLAlchemy change detection for JSON
            flag_modified(ucs, "settings")
            
            safe_commit(db.session)
        except Exception as e:
            import traceback
            traceback.print_exc()
            
        return jsonify({
            'success': True, 
            'redirect_url': url_for('vocabulary.typing.session_page')
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
        return redirect(url_for('vocabulary.dashboard'))
        
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    # Get params (Already in session, but we might pass to template if needed)
    custom_pairs = session_data.get('custom_pairs')
    count = session_data.get('count', 10)
    
    return render_dynamic_template('pages/learning/vocabulary/typing/session/index.html',
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
        if count is None: count = session_data.get('count')
        if not custom_pairs_str and session_data.get('custom_pairs'):
            custom_pairs = session_data.get('custom_pairs')

    # Fallback default (None means not provided, 0 means unlimited)
    if count is None: count = 10
    
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
    
    # [NEW] Session Persistence Logic
    from mindstack_app.models import LearningSession
    db_session_id = session_data.get('db_session_id')
    processed_ids = []
    
    # 1. Deterministic Shuffle (if we have a session)
    import random
    if db_session_id:
        # Use session_id as seed to ensure same order every reload
        random.Random(str(db_session_id)).shuffle(items)
        
        active_session = LearningSession.query.get(db_session_id)
        if active_session and active_session.processed_item_ids:
            processed_ids = active_session.processed_item_ids
    else:
        # Fallback random for stateless play
        random.shuffle(items)

    # 2. Filter out processed items
    if processed_ids:
        items = [i for i in items if i['id'] not in processed_ids]

    if len(items) < 1:
        # Check if we are actually complete
        if db_session_id:
             return jsonify({'success': True, 'items': [], 'complete': True, 'message': 'Session complete'}), 200
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    # 3. Limit count
    # count=0 means unlimited (all items), otherwise limit to count
    selected = items if count <= 0 else items[:min(count, len(items))]
    
    return jsonify({
        'success': True,
        'items': selected,
        'total': len(selected)
    })


@typing_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API to check typed answer."""
    from flask import session
    from mindstack_app.modules.flashcard.services.session_service import LearningSessionService

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
        from mindstack_app.modules.learning.services.fsrs_service import FsrsService
        from mindstack_app.utils.db_session import safe_commit
        from mindstack_app.models import db

        progress, srs_result = FsrsService.process_answer(
            user_id=current_user.user_id,
            item_id=item_id,
            quality=1,  # Dummy quality, derived implicitly from typing accuracy
            mode='typing',
            duration_ms=duration_ms,
            target_text=correct_answer,
            user_answer=user_answer
        )
        
        # Manually construct srs_result dict if needed for response or use srs_result object
        # The original code returned srs_result object or dict? process_interaction likely returned dict.
        # FsrsService.process_answer returns (progress, srs_result_obj).
        # We should serialize srs_result object to dict for JSON.
        from dataclasses import asdict
        srs_result_dict = asdict(srs_result)
        srs_result_dict['next_due'] = srs_result.next_review.isoformat() if srs_result.next_review else None
        
        safe_commit(db.session)
        result['srs'] = srs_result_dict
        
        # Update DB Session
        session_data = session.get('typing_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            result_type = 'correct' if result.get('correct') else 'incorrect'
            # Calculate points (simple logic for now)
            points = 10 if result.get('correct') else 0
            
            LearningSessionService.update_progress(
                session_id=db_session_id,
                item_id=item_id,
                result_type=result_type,
                points=points
            )


@typing_bp.route('/api/end_session', methods=['POST'])
@login_required
def end_session():
    """End the typing session."""
    from flask import session
    from mindstack_app.modules.flashcard.services.session_service import LearningSessionService
    
    try:
        session_data = session.get('typing_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            LearningSessionService.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        # Optional: Clear session data if you want to force a fresh start next time
        # session.pop('typing_session', None)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

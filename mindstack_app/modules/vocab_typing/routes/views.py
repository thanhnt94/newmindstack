# File: vocabulary/routes/typing.py
# Typing Learning Mode Routes

from flask import render_template, request, jsonify, abort, url_for, session, redirect
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import blueprint
from ..logics.typing_logic import get_typing_eligible_items, check_typing_answer
from mindstack_app.modules.vocab_mcq.logics.mcq_logic import get_available_content_keys
from mindstack_app.models import LearningContainer, UserContainerState, LearningSession, LearningItem, LearningProgress, db
from mindstack_app.utils.db_session import safe_commit
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone

@blueprint.route('/typing/setup/<int:set_id>')
@login_required
def typing_setup(set_id):
    """Typing setup page - choose columns."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_typing_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi gõ đáp án")
    
    available_keys = get_available_content_keys(set_id)
    
    base_query = LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD')
    count_new = base_query.filter(~LearningItem.progress_records.any()).count()
    now = datetime.now(timezone.utc)
    count_review = base_query.join(LearningProgress).filter(LearningProgress.fsrs_due <= now).count()
    count_learned = base_query.join(LearningProgress).count()
    
    from mindstack_app.modules.fsrs.services.hard_item_service import FSRSHardItemService as HardItemService
    count_hard = HardItemService.get_hard_count(current_user.user_id, set_id)
    count_random = len(items)

    saved_settings = {}
    default_settings = {}
    
    if container.settings and container.settings.get('typing'):
        default_settings = container.settings.get('typing').copy()
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('typing'):
            saved_settings = ucs.settings.get('typing', {})
    except Exception as e:
        pass

    return render_dynamic_template('modules/learning/vocab_typing/setup/index.html',
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


@blueprint.route('/typing/start', methods=['POST'])
@login_required
def typing_start_session():
    """Start a typing session: Save settings and redirect."""
    try:
        from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
        
        data = request.get_json()
        
        set_id = data.get('set_id')
        mode = data.get('mode', 'custom')
        count = data.get('count', 10)
        use_custom_config = data.get('use_custom_config', False)
        custom_pairs = data.get('custom_pairs')
        
        if not set_id:
            return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        session['typing_session'] = {
            'set_id': set_id,
            'mode': mode,
            'count': count,
            'custom_pairs': custom_pairs
        }
        
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

        try:
            ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
                db.session.add(ucs)
            
            new_settings = dict(ucs.settings or {})
            if 'typing' not in new_settings: new_settings['typing'] = {}
            
            new_settings['typing']['mode'] = mode
            if count is not None:
                new_settings['typing']['count'] = int(count)
            else:
                new_settings['typing']['count'] = 10
            new_settings['typing']['use_custom_config'] = bool(use_custom_config)
            if custom_pairs:
                new_settings['typing']['custom_pairs'] = custom_pairs
            
            ucs.settings = new_settings
            flag_modified(ucs, "settings")
            safe_commit(db.session)
        except Exception as e:
            import traceback
            traceback.print_exc()
            
        return jsonify({
            'success': True, 
            'redirect_url': url_for('vocab_typing.typing_session_page') 
        })
    except Exception as outer_e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f"Server Error: {str(outer_e)}"}), 500


@blueprint.route('/typing/session/')
@login_required
def typing_session_page():
    """Typing learning session page."""
    session_data = session.get('typing_session', {})
    set_id = session_data.get('set_id')
    
    if not set_id:
        return redirect(url_for('vocabulary.dashboard_home')) # Assuming dashboard route
        
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    custom_pairs = session_data.get('custom_pairs')
    count = session_data.get('count', 10)
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        container=container,
        custom_pairs=custom_pairs,
        count=count
    )


@blueprint.route('/typing/api/items/<int:set_id>')
@login_required
def typing_api_get_items(set_id):
    """API to get items for a typing session."""
    count = request.args.get('count', type=int)
    custom_pairs_str = request.args.get('custom_pairs', '')
    
    custom_pairs = None
    
    session_data = session.get('typing_session', {})
    if session_data.get('set_id') == set_id:
        if count is None: count = session_data.get('count')
        if not custom_pairs_str and session_data.get('custom_pairs'):
            custom_pairs = session_data.get('custom_pairs')

    if count is None: count = 10
    
    if custom_pairs_str:
        try:
            import json
            custom_pairs = json.loads(custom_pairs_str)
        except:
            pass

    mode = session_data.get('mode', 'custom')

    items = get_typing_eligible_items(set_id, custom_pairs=custom_pairs, mode=mode)
    
    db_session_id = session_data.get('db_session_id')
    processed_ids = []
    
    import random
    if db_session_id:
        random.Random(str(db_session_id)).shuffle(items)
        active_session = LearningSession.query.get(db_session_id)
        if active_session and active_session.processed_item_ids:
            processed_ids = active_session.processed_item_ids
    else:
        random.shuffle(items)

    if processed_ids:
        items = [i for i in items if i['id'] not in processed_ids]

    if len(items) < 1:
        if db_session_id:
             return jsonify({'success': True, 'items': [], 'complete': True, 'message': 'Session complete'}), 200
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    selected = items if count <= 0 else items[:min(count, len(items))]
    
    return jsonify({
        'success': True,
        'items': selected,
        'total': len(selected)
    })


@blueprint.route('/typing/api/check', methods=['POST'])
@login_required
def typing_api_check_answer():
    """API to check typed answer."""
    from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService

    data = request.get_json()
    correct_answer = data.get('correct_answer', '')
    user_answer = data.get('user_answer', '')
    duration_ms = data.get('duration_ms', 0)
    
    result = check_typing_answer(correct_answer, user_answer)
    result['user_answer'] = user_answer
    result['duration_ms'] = duration_ms
    
    item_id = data.get('item_id')
    if item_id:
        from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
        
        progress, srs_result = FsrsService.process_answer(
            user_id=current_user.user_id,
            item_id=item_id,
            quality=1,
            mode='typing',
            duration_ms=duration_ms,
            target_text=correct_answer,
            user_answer=user_answer
        )
        
        from dataclasses import asdict
        srs_result_dict = asdict(srs_result)
        srs_result_dict['next_due'] = srs_result.next_review.isoformat() if srs_result.next_review else None
        
        safe_commit(db.session)
        result['srs'] = srs_result_dict
        
        session_data = session.get('typing_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            result_type = 'correct' if result.get('correct') else 'incorrect'
            points = 10 if result.get('correct') else 0
            
            LearningSessionService.update_progress(
                session_id=db_session_id,
                item_id=item_id,
                result_type=result_type,
                points=points
            )
            
    return jsonify(result)


@blueprint.route('/typing/api/end_session', methods=['POST'])
@login_required
def typing_end_session():
    """End the typing session."""
    from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
    
    try:
        session_data = session.get('typing_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            LearningSessionService.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

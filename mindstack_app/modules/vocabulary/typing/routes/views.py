# File: vocabulary/routes/typing.py
# Typing (Practice) Routes for Vocabulary Learning

import json
from flask import render_template, request, jsonify, abort, session, current_app, url_for, redirect
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import typing_bp as blueprint
from ..interface import VocabTypingInterface as TypingInterface
from mindstack_app.models import LearningContainer, UserContainerState, LearningItem, db
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.core.signals import card_reviewed

@blueprint.route('/typing/setup/<int:set_id>')
@login_required
def typing_setup(set_id):
    """Typing setup page - choose mode, columns, number of questions."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = TypingInterface.get_typing_eligible_items(set_id, current_user.user_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ đã học để luyện gõ (Chế độ ôn tập)")
    
    available_keys = TypingInterface.get_available_content_keys(set_id)
    from mindstack_app.modules.vocabulary.interface import VocabularyInterface
    mode_counts = VocabularyInterface.get_mode_counts(current_user.user_id, set_id)

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
        total_items=len(items),
        available_keys=available_keys,
        mode_counts=mode_counts,
        saved_settings=saved_settings,
        default_settings=default_settings
    )

@blueprint.route('/typing/session/<int:set_id>')
@login_required
def typing_session(set_id):
    """Typing learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = TypingInterface.get_typing_eligible_items(set_id, current_user.user_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ đã học để luyện gõ (Chế độ ôn tập)")
    
    ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
    saved_typing = ucs.settings.get('typing', {}) if ucs and ucs.settings else {}

    container_typing = (container.settings or {}).get('typing', {})
    
    req_count = request.args.get('count') or request.args.get('limit')
    count = int(req_count) if req_count is not None else saved_typing.get('count', container_typing.get('count', 0))
    
    req_mode = request.args.get('mode')
    mode = req_mode if req_mode is not None else saved_typing.get('mode', container_typing.get('mode', 'front_back'))
    
    custom_pairs = None
    custom_pairs_str = request.args.get('custom_pairs', '')
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except: pass
    
    if not custom_pairs:
        custom_pairs = saved_typing.get('custom_pairs') or container_typing.get('pairs') or container_typing.get('custom_pairs')
            
    try:
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'typing' not in new_settings: new_settings['typing'] = {}
        
        new_settings['typing']['count'] = count
        new_settings['typing']['mode'] = mode
        
        if custom_pairs:
            new_settings['typing']['custom_pairs'] = custom_pairs
            
        ucs.settings = new_settings
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ucs, "settings")
        safe_commit(db.session)
    except Exception as e:
        current_app.logger.error(f"[VOCAB_TYPING] Error saving settings: {e}")
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        container=container,
        total_items=len(items),
        mode=mode,
        count=count,
        custom_pairs=custom_pairs,
        auto_audio=saved_typing.get('auto_audio', True)
    )

# ALIAS for backward compatibility
@blueprint.route('/session/<int:set_id>')
@login_required
def typing_session_page(set_id):
    return redirect(url_for('vocab_typing.typing_session', set_id=set_id))

@blueprint.route('/typing/setup/save/<int:set_id>', methods=['POST'])
@login_required
def typing_save_setup(set_id):
    """API to save Typing settings before starting session (for clean URLs)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        mode = data.get('mode', 'custom')
        study_mode = data.get('study_mode', 'review')
        count = data.get('count', 0)
        custom_pairs = data.get('custom_pairs')
        use_custom_config = data.get('use_custom_config', False)
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'typing' not in new_settings: new_settings['typing'] = {}
        
        new_settings['typing']['mode'] = mode
        new_settings['typing']['study_mode'] = study_mode
        new_settings['typing']['count'] = int(count) if count is not None else 0
        new_settings['typing']['use_custom_config'] = bool(use_custom_config)
        new_settings['typing']['auto_audio'] = bool(data.get('auto_audio', True))
        
        if custom_pairs:
            new_settings['typing']['custom_pairs'] = custom_pairs
            
        if 'typing_session_data' in new_settings:
            del new_settings['typing_session_data']
            
        ucs.settings = new_settings
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ucs, "settings")
        safe_commit(db.session)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/typing/api/items/<int:set_id>')
@login_required
def typing_api_get_items(set_id):
    """API to get Typing items for a session, with session persistence."""
    try:
        from ..services.typing_session_manager import TypingSessionManager
        from mindstack_app.modules.session.interface import SessionInterface
        
        count = request.args.get('count', 0, type=int)
        mode = request.args.get('mode', 'front_back')
        study_mode = request.args.get('study_mode', 'review')
        custom_pairs_str = request.args.get('custom_pairs', '')
        
        custom_pairs = None
        if custom_pairs_str:
            try:
                custom_pairs = json.loads(custom_pairs_str)
                if custom_pairs:
                    custom_pairs = [p for p in custom_pairs if p.get('enabled', True)]
            except:
                pass

        manager = TypingSessionManager.load_from_db(current_user.user_id, set_id)
        
        if manager and count == 0:
             current_count = manager.params.get('count', 10)
             if current_count != 0 and len(manager.questions) <= 10:
                 if manager.db_session_id:
                     SessionInterface.complete_session(manager.db_session_id)
                 manager = None

        if manager:
            request_params = {
                'count': count, 'mode': mode, 'custom_pairs': custom_pairs, 'study_mode': study_mode
            }
            if manager.params == request_params:
                response = manager.get_session_data()
                response['is_restored'] = True
                return jsonify(response)

        manager = TypingSessionManager(current_user.user_id, set_id)
        success, message = manager.initialize_session(
            count=count, mode=mode, custom_pairs=custom_pairs, study_mode=study_mode
        )
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
            
        return jsonify(manager.get_session_data())

    except Exception as e:
        current_app.logger.error(f"[VOCAB_TYPING] API Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/typing/api/next/<int:set_id>', methods=['POST'])
@login_required
def typing_api_next_question(set_id):
    """API to advance to the next Typing question in the session."""
    from ..services.typing_session_manager import TypingSessionManager
    manager = TypingSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'No active session'}), 404
        
    success = manager.next_item()
    
    if not success and manager.params.get('count') == 0:
        if manager.start_next_cycle():
            return jsonify({
                'success': True, 
                'currentIndex': 0,
                'new_cycle': True,
                'questions': manager.questions
            })

    return jsonify({'success': success, 'currentIndex': manager.currentIndex})

@blueprint.route('/typing/api/check', methods=['POST'])
@login_required
def typing_api_check_answer():
    """API to check Typing answer."""
    from ..services.typing_session_manager import TypingSessionManager
    data = request.get_json()
    set_id = data.get('set_id')
    user_input = data.get('user_input', '').strip()
    item_id = data.get('item_id')
    
    if set_id is None:
        return jsonify({'success': False, 'message': 'Missing set_id'}), 400
        
    manager = TypingSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    result = manager.check_answer(user_input)
    if not result['success']:
        return jsonify(result), 400
        
    from mindstack_app.modules.scoring.interface import ScoringInterface
    point_value = ScoringInterface.get_score_value('VOCAB_TYPING_CORRECT_BONUS')
    
    duration_ms = data.get('duration_ms', 0)
    result['user_answer'] = user_input
    result['duration_ms'] = duration_ms
    result['quality'] = 5 if result['is_correct'] else 0
    result['score_change'] = point_value if result['is_correct'] else 0
    result['updated_total_score'] = current_user.total_score
    
    if item_id:
        try:
            # Map outcome for logging/points consistency (Correct = 3, Incorrect = 1)
            fsrs_quality = 3 if result['is_correct'] else 1

            # [REMOVED] FSRS update as requested
            
            # [EMIT] Core signal for Gamification to award points
            try:
                # Fetch item for type if not provided, fallback to FLASHCARD
                item = LearningItem.query.get(item_id)
                item_type = item.item_type if item else 'FLASHCARD'
                
                card_reviewed.send(
                    None,
                    user_id=current_user.user_id,
                    item_id=item_id,
                    quality=fsrs_quality,
                    is_correct=result['is_correct'],
                    learning_mode='typing',
                    score_points=result['score_change'],
                    item_type=item_type,
                    reason=f"Vocab Typing Practice {'Correct' if result['is_correct'] else 'Incorrect'}"
                )
            except Exception as e_signal:
                 current_app.logger.error(f"[VOCAB_TYPING] Signal emit error: {e_signal}")

            # [LOG] Record learning history (Activity log)
            try:
                from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
                # No FSRS snapshot
                
                LearningHistoryInterface.record_log(
                    user_id=current_user.user_id,
                    item_id=item_id,
                    result_data={
                        'rating': fsrs_quality,
                        'user_answer': result.get('user_answer'),
                        'is_correct': result['is_correct'],
                        'review_duration': result.get('duration_ms', 0)
                    },
                    context_data={
                        'session_id': manager.db_session_id,
                        'container_id': set_id,
                        'learning_mode': 'typing'
                    },
                    game_snapshot={'score_earned': result['score_change']}
                )
            except Exception as e_log:
                current_app.logger.error(f"[VOCAB_TYPING] History log error: {e_log}")

            # Get updated total score
            result['updated_total_score'] = current_user.total_score
            
        except Exception as e:
            current_app.logger.error(f"Typing result processing failed: {e}")
            
    if manager.db_session_id:
        result['session_id'] = manager.db_session_id
    
    return jsonify(result)

@blueprint.route('/typing/api/end_session', methods=['POST'])
@login_required
def typing_end_session():
    """End the Typing session."""
    from ..services.typing_session_manager import TypingSessionManager
    try:
        data = request.get_json(silent=True) or {}
        set_id = data.get('set_id') or request.args.get('set_id')
        
        if not set_id:
             return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        manager = TypingSessionManager.load_from_db(current_user.user_id, set_id)
        if manager:
            from mindstack_app.modules.session.interface import SessionInterface
            session_id = manager.db_session_id
            if session_id:
                SessionInterface.complete_session(session_id)
            manager.clear_session()
            return jsonify({'success': True, 'session_id': session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

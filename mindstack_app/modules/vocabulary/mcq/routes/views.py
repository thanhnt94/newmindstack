# File: vocabulary/routes/mcq.py
# MCQ (Multiple Choice Quiz) Routes for Vocabulary Learning

import json
from flask import render_template, request, jsonify, abort, session, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import mcq_bp as blueprint
from ..interface import VocabMCQInterface as MCQInterface
from mindstack_app.models import LearningContainer, UserContainerState, LearningItem, db
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.core.signals import card_reviewed

@blueprint.route('/mcq/setup/<int:set_id>')
@login_required
def mcq_setup(set_id):
    """MCQ setup page - choose mode, columns, number of questions."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = MCQInterface.get_mcq_eligible_items(set_id, current_user.user_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ đã học để chơi trắc nghiệm (Chế độ ôn tập)")
    
    available_keys = MCQInterface.get_available_content_keys(set_id)
    # Using module-specific logic for counts if needed, or delegation
    from mindstack_app.modules.vocabulary.interface import VocabularyInterface
    mode_counts = VocabularyInterface.get_mode_counts(current_user.user_id, set_id)

    saved_settings = {}
    default_settings = {}
    
    if container.settings and container.settings.get('mcq'):
        default_settings = container.settings.get('mcq').copy()
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('mcq'):
            saved_settings = ucs.settings.get('mcq', {})
    except Exception as e:
        pass
    
    return render_dynamic_template('modules/learning/vocab_mcq/setup/index.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys,
        mode_counts=mode_counts,
        saved_settings=saved_settings,
        default_settings=default_settings
    )


@blueprint.route('/mcq/api/keys/<int:set_id>')
@login_required
def mcq_api_get_keys(set_id):
    """API to get available content keys for a set."""
    keys = MCQInterface.get_available_content_keys(set_id)
    return jsonify({
        'success': True,
        'keys': keys
    })


@blueprint.route('/mcq/session/<int:set_id>')
@login_required
def mcq_session(set_id):
    """MCQ learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = MCQInterface.get_mcq_eligible_items(set_id, current_user.user_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ đã học để chơi trắc nghiệm (Chế độ ôn tập)")
    
    ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
    saved_mcq = ucs.settings.get('mcq', {}) if ucs and ucs.settings else {}

    # Load defaults from container if not specified in user settings
    container_mcq = (container.settings or {}).get('mcq', {})
    
    # Mode, Count, Choices fallbacks
    # Prioritize request.args, then saved user settings, then container defaults
    req_count = request.args.get('count') or request.args.get('limit')
    count = int(req_count) if req_count is not None else saved_mcq.get('count', container_mcq.get('count', 0))
    
    req_mode = request.args.get('mode')
    mode = req_mode if req_mode is not None else saved_mcq.get('mode', container_mcq.get('mode', 'front_back'))
    
    req_choices = request.args.get('choices')
    choices = int(req_choices) if req_choices is not None else saved_mcq.get('choices', container_mcq.get('choices', 0))
    
    custom_pairs = None
    custom_pairs_str = request.args.get('custom_pairs', '')
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except: pass
    
    if not custom_pairs:
        # Fallback to saved or container defaults
        custom_pairs = saved_mcq.get('custom_pairs') or container_mcq.get('pairs') or container_mcq.get('custom_pairs')
            
    try:
        if not ucs:
            ucs = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                settings={}
            )
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'mcq' not in new_settings: new_settings['mcq'] = {}
        
        new_settings['mcq']['count'] = count
        new_settings['mcq']['choices'] = choices
        
        if custom_pairs:
            new_settings['mcq']['custom_pairs'] = custom_pairs
        elif mode == 'custom':
            pass
            
        ucs.settings = new_settings
        safe_commit(db.session)
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    return render_dynamic_template('modules/learning/vocab_mcq/session/index.html',
        container=container,
        total_items=len(items),
        mode=mode,
        count=count,
        choices=choices,
        custom_pairs=custom_pairs
    )


@blueprint.route('/mcq/setup/save/<int:set_id>', methods=['POST'])
@login_required
def mcq_save_setup(set_id):
    """API to save MCQ settings before starting session (for clean URLs)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        mode = data.get('mode', 'custom')
        study_mode = data.get('study_mode', 'review')
        count = data.get('count', 0)
        choices = data.get('choices', 4)
        custom_pairs = data.get('custom_pairs')
        use_custom_config = data.get('use_custom_config', False)
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'mcq' not in new_settings: new_settings['mcq'] = {}
        
        new_settings['mcq']['mode'] = mode
        new_settings['mcq']['study_mode'] = study_mode
        if count is not None:
             new_settings['mcq']['count'] = int(count)
        else:
             new_settings['mcq']['count'] = 0
             
        new_settings['mcq']['choices'] = int(choices) if choices is not None else 0
        new_settings['mcq']['use_custom_config'] = bool(use_custom_config)
        
        if custom_pairs:
            new_settings['mcq']['custom_pairs'] = custom_pairs
            
        if 'mcq_session_data' in new_settings:
            del new_settings['mcq_session_data']
            
        ucs.settings = new_settings
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ucs, "settings")
        
        safe_commit(db.session)
        
        mcq_session_key = f'mcq_session_{set_id}'
        if mcq_session_key in session:
            session.pop(mcq_session_key)
            session.modified = True
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@blueprint.route('/mcq/api/items/<int:set_id>')
@login_required
def mcq_api_get_items(set_id):
    """API to get MCQ items for a session, with session persistence."""
    try:
        from ..services.mcq_session_manager import MCQSessionManager
        from mindstack_app.modules.session.interface import SessionInterface
        
        # Default to 0 (Unlimited) instead of 10
        count = request.args.get('count', 0, type=int)
        mode = request.args.get('mode', 'front_back')
        study_mode = request.args.get('study_mode', 'review')
        num_choices = request.args.get('choices', 0, type=int)
        custom_pairs_str = request.args.get('custom_pairs', '')
        
        custom_pairs = None
        if custom_pairs_str:
            try:
                custom_pairs = json.loads(custom_pairs_str)
                if custom_pairs:
                    custom_pairs = [p for p in custom_pairs if p.get('enabled', True)]
            except:
                pass

        manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
        
        # Auto-restart if user requests Unlimited (count=0/None) but active session is limited (e.g. 10 items)
        # This matches the logic added to Typing mode
        if manager and count == 0:
             # Check if current session was created with a limit (implied by total questions being exactly 10, often default)
             # Better: Check manager params if available
             current_count = manager.params.get('count', 10)
             if current_count != 0 and len(manager.questions) <= 10:
                 # Restart session to get full list
                 if manager.db_session_id:
                     SessionInterface.complete_session(manager.db_session_id)
                 manager = None

        if manager:
            request_params = {
                'count': count, 'mode': mode, 'choices': num_choices, 'custom_pairs': custom_pairs, 'study_mode': study_mode
            }
            if manager.params == request_params:
                current_app.logger.info(f"[VOCAB_MCQ] Resuming session for user {current_user.user_id}, set {set_id}. Current index: {manager.currentIndex}")
                response = manager.get_session_data()
                response['is_restored'] = True
                return jsonify(response)

        manager = MCQSessionManager(current_user.user_id, set_id)
        success, message = manager.initialize_session(
            count=count, mode=mode, choices=num_choices, custom_pairs=custom_pairs, study_mode=study_mode
        )
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
            
        current_app.logger.info(f"[VOCAB_MCQ] Started NEW session for user {current_user.user_id}, set {set_id}. Mode: {mode}, Count: {count}")
        return jsonify(manager.get_session_data())

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@blueprint.route('/mcq/api/next/<int:set_id>', methods=['POST'])
@login_required
def mcq_api_next_question(set_id):
    """API to advance to the next MCQ question in the session."""
    from ..services.mcq_session_manager import MCQSessionManager
    manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'No active session'}), 404
        
    old_index = manager.currentIndex
    success = manager.next_item()
    if success:
        current_app.logger.info(f"[VOCAB_MCQ] Advanced index from {old_index} to {manager.currentIndex} for user {current_user.user_id}, set {set_id}")
    
    # [NEW] Auto-start next cycle for Unlimited mode
    if not success and manager.params.get('count') == 0:
        if manager.start_next_cycle():
            current_app.logger.info(f"[VOCAB_MCQ] Starting NEW CYCLE for user {current_user.user_id}, set {set_id} (Unlimited mode)")
            return jsonify({
                'success': True, 
                'currentIndex': 0,
                'new_cycle': True,
                'questions': manager.questions
            })

    return jsonify({'success': success, 'currentIndex': manager.currentIndex})


@blueprint.route('/mcq/api/check', methods=['POST'])
@login_required
def mcq_api_check_answer():
    """API to check MCQ answer."""
    from ..services.mcq_session_manager import MCQSessionManager
    data = request.get_json()
    set_id = data.get('set_id')
    user_answer_index = data.get('user_answer_index')
    item_id = data.get('item_id')
    
    if set_id is None or user_answer_index is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    result = manager.check_answer(user_answer_index)
    current_app.logger.info(f"[VOCAB_MCQ] Answer check for user {current_user.user_id}, item {item_id}: Correct={result.get('is_correct')}")
    if not result['success']:
        return jsonify(result), 400
        
    from mindstack_app.modules.scoring.interface import ScoringInterface
    point_value = ScoringInterface.get_score_value('VOCAB_MCQ_CORRECT_BONUS')
    
    user_answer_text = data.get('user_answer_text')
    duration_ms = data.get('duration_ms', 0)
    
    result['user_answer'] = user_answer_text
    result['duration_ms'] = duration_ms
    result['quality'] = 5 if result['is_correct'] else 0
    result['score_change'] = point_value if result['is_correct'] else 0
    result['updated_total_score'] = current_user.total_score
    
    if item_id:
        try:
            # Map MCQ outcome for logging/points consistency (Correct = 3, Incorrect = 1)
            fsrs_quality = 3 if result['is_correct'] else 1
            
            # [RE-ENABLED] FSRS update (process_interaction) as requested by user
            # We use only_count=True to increment MCQ/TOTAL reps without affecting FSRS S/D/R
            try:
                from mindstack_app.modules.fsrs.interface import FSRSInterface
                fsrs_res = FSRSInterface.process_interaction(
                    user_id=current_user.user_id,
                    item_id=item_id,
                    quality=fsrs_quality,
                    mode='mcq',
                    only_count=True
                )
                # Merge FSRS result into the main response
                result.update(fsrs_res)
            except Exception as e_fsrs:
                current_app.logger.error(f"[VOCAB_MCQ] FSRS interaction error: {e_fsrs}")

            # [EMIT] Core signal for Gamification to award points
            try:
                # Fetch item for type if not provided, fallback to FLASHCARD for points consistency
                item = LearningItem.query.get(item_id)
                item_type = item.item_type if item else 'FLASHCARD'
                
                card_reviewed.send(
                    None,
                    user_id=current_user.user_id,
                    item_id=item_id,
                    quality=fsrs_quality,
                    is_correct=result['is_correct'],
                    learning_mode='mcq',
                    score_points=result['score_change'],
                    item_type=item_type,
                    reason=f"Vocab MCQ Practice {'Correct' if result['is_correct'] else 'Incorrect'}"
                )
            except Exception as e_signal:
                 current_app.logger.error(f"[VOCAB_MCQ] Signal emit error: {e_signal}")
            
            # [LOG] Record learning history (Activity log)
            try:
                from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
                # No FSRS snapshot since we aren't updating it
                
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
                        'learning_mode': 'mcq'
                    },
                    game_snapshot={'score_earned': result['score_change']}
                )
            except Exception as e_log:
                current_app.logger.error(f"[VOCAB_MCQ] History log error: {e_log}")

            # Get updated total score
            result['updated_total_score'] = current_user.total_score
        except Exception as e:
            import logging
            logging.error(f"MCQ result processing failed: {e}")
            
    if manager.db_session_id:
        result['session_id'] = manager.db_session_id
    
    return jsonify(result)

@blueprint.route('/mcq/api/cycle/next', methods=['POST'])
@login_required
def mcq_next_cycle():
    """Starts the next random cycle for unlimited mode."""
    from ..services.mcq_session_manager import MCQSessionManager
    try:
        data = request.get_json(silent=True) or {}
        set_id = data.get('set_id') or request.args.get('set_id')
        
        if not set_id:
             return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
        if manager:
            if manager.start_next_cycle():
                return jsonify({
                    'success': True, 
                    'questions': manager.questions,
                    'currentIndex': 0
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to start next cycle (no questions?)'})
        
        return jsonify({'success': False, 'message': 'Session not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/mcq/api/end_session', methods=['POST'])
@login_required
def mcq_end_session():
    """End the MCQ session."""
    from ..services.mcq_session_manager import MCQSessionManager
    try:
        data = request.get_json(silent=True) or {}
        set_id = data.get('set_id') or request.args.get('set_id')
        
        if not set_id:
             return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
        if manager:
            from mindstack_app.modules.session.interface import SessionInterface
            if manager.db_session_id:
                SessionInterface.complete_session(manager.db_session_id)
            
            # [FIX] Clear session data so it doesn't resume
            manager.clear_session()
            
            current_app.logger.info(f"[VOCAB_MCQ] Session {manager.db_session_id} ENDED for user {current_user.user_id}, set {set_id}")
            return jsonify({'success': True, 'session_id': manager.db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        # [FALLBACK] If load_from_db fails (e.g. corrupt data), FORCE CLEAR
        try:
            MCQSessionManager.static_clear_session(current_user.user_id, set_id)
            return jsonify({'success': True, 'message': 'Session force cleared'})
        except:
            pass
            
        return jsonify({'success': False, 'message': str(e)}), 500

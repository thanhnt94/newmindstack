# File: vocabulary/routes/mcq.py
# MCQ (Multiple Choice Quiz) Routes for Vocabulary Learning

import json
from flask import render_template, request, jsonify, abort, session
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import mcq_bp as blueprint
from ..interface import VocabMCQInterface as MCQInterface
from mindstack_app.models import LearningContainer, UserContainerState, db
from mindstack_app.utils.db_session import safe_commit

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

    if not saved_mcq and container.settings and container.settings.get('mcq'):
        default_mcq = container.settings.get('mcq')
        saved_mcq = default_mcq.copy()
        if 'pairs' in default_mcq:
             saved_mcq['custom_pairs'] = default_mcq['pairs']

    mode = request.args.get('mode', saved_mcq.get('mode', 'front_back'))
    count = request.args.get('count', saved_mcq.get('count', 10), type=int)
    choices = request.args.get('choices', saved_mcq.get('choices', 0), type=int)
    
    custom_pairs = None
    custom_pairs_str = request.args.get('custom_pairs', '')
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except: pass
    
    if not custom_pairs and 'custom_pairs' in saved_mcq:
        custom_pairs = saved_mcq['custom_pairs']
            
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
        count = data.get('count', 10)
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
        if count is not None:
             new_settings['mcq']['count'] = int(count)
        else:
             new_settings['mcq']['count'] = 10
             
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
        
        count = request.args.get('count', 10, type=int)
        mode = request.args.get('mode', 'front_back')
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
        if manager:
            request_params = {
                'count': count, 'mode': mode, 'choices': num_choices, 'custom_pairs': custom_pairs
            }
            if manager.params == request_params:
                response = manager.get_session_data()
                response['is_restored'] = True
                return jsonify(response)

        manager = MCQSessionManager(current_user.user_id, set_id)
        success, message = manager.initialize_session(
            count=count, mode=mode, choices=num_choices, custom_pairs=custom_pairs
        )
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
            
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
        
    success = manager.next_item()
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
    if not result['success']:
        return jsonify(result), 400
        
    user_answer_text = data.get('user_answer_text')
    duration_ms = data.get('duration_ms', 0)
    result['user_answer'] = user_answer_text
    result['duration_ms'] = duration_ms
    result['quality'] = 5 if result['is_correct'] else 0
    result['score_change'] = 10 if result['is_correct'] else 0
    
    if item_id:
        try:
            from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
            srs_result = FsrsService.process_interaction(
                user_id=current_user.user_id,
                item_id=item_id,
                mode='mcq',
                result_data=result
            )
            safe_commit(db.session)
            result.update(srs_result)
        except Exception as e:
            import logging
            logging.error(f"SRS update failed for MCQ: {e}")
            
    if manager.db_session_id:
        result['session_id'] = manager.db_session_id
    
    return jsonify(result)

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
                return jsonify({'success': True, 'session_id': manager.db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

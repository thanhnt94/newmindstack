# File: vocabulary/mcq/routes.py
# MCQ (Multiple Choice Quiz) Routes for Vocabulary Learning

import json
from flask import render_template, request, jsonify, abort
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from . import mcq_bp
from .logic import get_mcq_eligible_items, generate_mcq_question, check_mcq_answer, get_available_content_keys, get_mcq_mode_counts
from mindstack_app.models import LearningContainer, UserContainerState, db


@mcq_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """MCQ setup page - choose mode, columns, number of questions."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items count
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để chơi trắc nghiệm")
    
    # Get available content keys for custom column selection
    available_keys = get_available_content_keys(set_id)
    
    # Get learning statistics
    mode_counts = get_mcq_mode_counts(current_user.user_id, set_id)

    # [UPDATED] Load saved settings & container defaults
    saved_settings = {}
    default_settings = {}
    
    # 1. Get Container Defaults
    if container.settings and container.settings.get('mcq'):
        default_settings = container.settings.get('mcq').copy()
        # Map 'pairs' to 'custom_pairs' for consistency
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    # 2. Get User Settings
    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('mcq'):
            saved_settings = ucs.settings.get('mcq', {})
    except Exception as e:
        pass
    
    return render_dynamic_template('pages/learning/vocabulary/mcq/setup/index.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys,
        mode_counts=mode_counts,
        saved_settings=saved_settings,
        default_settings=default_settings
    )


@mcq_bp.route('/api/keys/<int:set_id>')
@login_required
def api_get_keys(set_id):
    """API to get available content keys for a set."""
    keys = get_available_content_keys(set_id)
    return jsonify({
        'success': True,
        'keys': keys
    })


@mcq_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """MCQ learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items
    items = get_mcq_eligible_items(set_id)
    if len(items) < 2:
        abort(400, description="Cần ít nhất 2 thẻ để chơi trắc nghiệm")
    
    # [UPDATED] Prioritize stored settings for clean URLs
    ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
    saved_mcq = ucs.settings.get('mcq', {}) if ucs and ucs.settings else {}

    # Fallback to container defaults if no user settings
    if not saved_mcq and container.settings and container.settings.get('mcq'):
        default_mcq = container.settings.get('mcq')
        saved_mcq = default_mcq.copy()
        if 'pairs' in default_mcq:
             saved_mcq['custom_pairs'] = default_mcq['pairs']

    # Get params (Query params take precedence for backward compatibility/direct links)
    mode = request.args.get('mode', saved_mcq.get('mode', 'front_back'))
    count = request.args.get('count', saved_mcq.get('count', 10), type=int)
    choices = request.args.get('choices', saved_mcq.get('choices', 4), type=int)
    
    # Get custom_pairs
    custom_pairs = None
    custom_pairs_str = request.args.get('custom_pairs', '')
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except: pass
    
    if not custom_pairs and 'custom_pairs' in saved_mcq:
        custom_pairs = saved_mcq['custom_pairs']
            
    # [UPDATED] Save settings to persistence
    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                settings={}
            )
            from mindstack_app.models import db
            db.session.add(ucs)
        
        # Update settings (using copy to ensure modification)
        new_settings = dict(ucs.settings or {})
        if 'mcq' not in new_settings: new_settings['mcq'] = {}
        
        # Update specific fields
        new_settings['mcq']['count'] = count
        new_settings['mcq']['choices'] = choices
        
        # Only save custom_pairs if explicitly provided (to avoid overwriting complex setup with simple mode?)
        # Actually mode 'custom' usually implies custom_pairs presence.
        if custom_pairs:
            new_settings['mcq']['custom_pairs'] = custom_pairs
        elif mode == 'custom':
            # If mode is custom but no pairs? Should not happen.
            pass
            
        ucs.settings = new_settings
        from mindstack_app.utils.db_session import safe_commit
        from mindstack_app.models import db
        safe_commit(db.session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Non-blocking error
    
    return render_dynamic_template('pages/learning/vocabulary/mcq/session/index.html',
        container=container,
        total_items=len(items),
        mode=mode,
        count=count,
        choices=choices,
        custom_pairs=custom_pairs
    )


@mcq_bp.route('/setup/save/<int:set_id>', methods=['POST'])
@login_required
def save_setup(set_id):
    """API to save MCQ settings before starting session (for clean URLs)."""
    import datetime
    def log_mcq(msg):
        with open('mcq_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")

    log_mcq(f"Received save_setup for set_id={set_id}")
    from flask import session
    
    try:
        data = request.get_json()
        if not data:
            log_mcq("No JSON data received in save_setup")
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        log_mcq(f"Payload keys: {list(data.keys())}")
        
        mode = data.get('mode', 'custom')
        count = data.get('count', 10)
        choices = data.get('choices', 4)
        custom_pairs = data.get('custom_pairs')
        use_custom_config = data.get('use_custom_config', False)
        
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            log_mcq(f"Creating new UserContainerState for user={current_user.user_id}, container={set_id}")
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        # Update settings
        new_settings = dict(ucs.settings or {})
        if 'mcq' not in new_settings: new_settings['mcq'] = {}
        
        new_settings['mcq']['mode'] = mode
        # Fix: Allow count=0 for unlimited. Only default to 10 if count is None or not present.
        if count is not None:
             new_settings['mcq']['count'] = int(count)
        else:
             new_settings['mcq']['count'] = 10
             
        new_settings['mcq']['choices'] = int(choices) if choices else 4
        new_settings['mcq']['use_custom_config'] = bool(use_custom_config)
        
        if custom_pairs:
            new_settings['mcq']['custom_pairs'] = custom_pairs
            
        # [CRITICAL] Clear existing DB-backed session data to force new generation
        if 'mcq_session_data' in new_settings:
            log_mcq("Clearing old mcq_session_data for fresh start")
            del new_settings['mcq_session_data']
            
        ucs.settings = new_settings
        
        # Trigger SQLAlchemy change detection for JSON
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ucs, "settings")
        
        log_mcq("Attempting safe_commit")
        safe_commit(db.session)
        log_mcq("save_setup successful")
        
        # Also clear legacy Flask session cache if any
        mcq_session_key = f'mcq_session_{set_id}'
        if mcq_session_key in session:
            session.pop(mcq_session_key)
            session.modified = True
            
        return jsonify({'success': True})
    except Exception as e:
        log_mcq(f"ERROR in save_setup: {str(e)}")
        import traceback
        log_mcq(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@mcq_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get MCQ items for a session, with session persistence."""
    import json
    import datetime
    def log_mcq(msg):
        with open('mcq_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")

    try:
        from .mcq_session_manager import MCQSessionManager
        
        count = request.args.get('count', 10, type=int)
        mode = request.args.get('mode', 'front_back')
        num_choices = request.args.get('choices', 4, type=int)
        custom_pairs_str = request.args.get('custom_pairs', '')
        
        log_mcq(f"api_get_items for set_id={set_id}")
        
        # Parse custom pairs early
        custom_pairs = None
        if custom_pairs_str:
            try:
                custom_pairs = json.loads(custom_pairs_str)
                # Filter enabled pairs only for processing
                if custom_pairs:
                    custom_pairs = [p for p in custom_pairs if p.get('enabled', True)]
            except:
                pass

        # Try to load existing session from DB
        manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
        if manager:
            log_mcq(f"  Manager FOUND in DB for set_id={set_id}")
            
            # Re-use session if params match (compare as objects!)
            request_params = {
                'count': count, 'mode': mode, 'choices': num_choices, 'custom_pairs': custom_pairs
            }
            
            log_mcq(f"Comparing params")
            log_mcq(f"  Existing count type: {type(manager.params.get('count'))}")
            log_mcq(f"  Requested count type: {type(count)}")
                
            if manager.params == request_params:
                log_mcq("  MATCH - Reusing existing session")
                response = manager.get_session_data()
                response['is_restored'] = True
                return jsonify(response)

        log_mcq("  NO MATCH or NO MANAGER - Initializing new session")
        # Initialize new session
        manager = MCQSessionManager(current_user.user_id, set_id)
        success, message = manager.initialize_session(
            count=count, mode=mode, choices=num_choices, custom_pairs=custom_pairs
        )
        
        if not success:
            log_mcq(f"  Initialization FAILED: {message}")
            return jsonify({'success': False, 'message': message}), 400
            
        return jsonify(manager.get_session_data())

    except Exception as e:
        log_mcq(f"ERROR in api_get_items: {str(e)}")
        import traceback
        log_mcq(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@mcq_bp.route('/api/next/<int:set_id>', methods=['POST'])
@login_required
def api_next_question(set_id):
    """API to advance to the next MCQ question in the session."""
    from .mcq_session_manager import MCQSessionManager
    manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'No active session'}), 404
        
    success = manager.next_item()
    return jsonify({'success': success, 'currentIndex': manager.currentIndex})


@mcq_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API to check MCQ answer."""
    from .mcq_session_manager import MCQSessionManager
    data = request.get_json()
    set_id = data.get('set_id')
    user_answer_index = data.get('user_answer_index')
    item_id = data.get('item_id')
    
    if set_id is None or user_answer_index is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
    if not manager:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    # The actual check logic is shared with the manager to update stats/answers
    result = manager.check_answer(user_answer_index)
    if not result['success']:
        return jsonify(result), 400
        
    # Enrich result with extra data for frontend/SRS
    user_answer_text = data.get('user_answer_text')
    duration_ms = data.get('duration_ms', 0)
    result['user_answer'] = user_answer_text
    result['duration_ms'] = duration_ms
    result['quality'] = 5 if result['is_correct'] else 0
    result['score_change'] = 10 if result['is_correct'] else 0
    
    # Update SRS if item_id provided
    if item_id:
        try:
            import logging
            from mindstack_app.modules.learning.services.fsrs_service import FsrsService
            from mindstack_app.utils.db_session import safe_commit
            from mindstack_app.models import db

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
            
    # Include session_id for frontend redirection
    if manager.db_session_id:
        result['session_id'] = manager.db_session_id
    
    return jsonify(result)

@mcq_bp.route('/api/end_session', methods=['POST'])
@login_required
def end_session():
    """End the MCQ session."""
    from .mcq_session_manager import MCQSessionManager
    try:
        data = request.get_json(silent=True) or {}
        set_id = data.get('set_id') or request.args.get('set_id')
        
        # If set_id not provided, try to find active session from DB helper
        if not set_id:
             # This might be tricky without set_id, but the frontend should send it.
             # Alternatively, we can check Flask session for 'mcq_session_set_id' if we stored it?
             # For now, require set_id or just fail gracefully.
             return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        manager = MCQSessionManager.load_from_db(current_user.user_id, set_id)
        if manager:
            # Complete the session
            from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService
            if manager.db_session_id:
                LearningSessionService.complete_session(manager.db_session_id)
                return jsonify({'success': True, 'session_id': manager.db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

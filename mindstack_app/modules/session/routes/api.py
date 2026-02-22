
# File: mindstack_app/modules/session/routes/api.py
from flask import request, jsonify, current_app, url_for, render_template
from flask_login import login_required, current_user
from .. import blueprint
from ..services.session_service import LearningSessionService
from mindstack_app.models import LearningContainer, db

def safe_url_for(endpoint, **values):
    try:
        return url_for(endpoint, **values)
    except Exception as e:
        current_app.logger.warning(f"[SESSION MODULE] Failed to build url for endpoint '{endpoint}': {e}")
        return '#'

def get_mode_description(session):
    """Generate a detailed breadcrumb-style description for a learning session."""
    module_name = "Từ vựng"
    
    # Map learning_mode to a display name
    mode_display = {
        'flashcard': 'Flashcard',
        'mcq': 'Trắc nghiệm',
        'quiz': 'Quiz',
        'typing': 'Gõ từ',
        'listening': 'Luyện nghe',
        'matching': 'Ghép thẻ',
        'speed': 'Ôn nhanh'
    }
    
    # Map mode_config_id to a specific sub-mode name
    sub_mode_map = {
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập đến hạn',
        'hard_only': 'Thẻ khó',
        'mixed_srs': 'SRS',
        'srs': 'SRS',
        'all_review': 'Tất cả',
        'mixed': 'Hỗn hợp'
    }
    
    main_mode = mode_display.get(session.learning_mode, session.learning_mode.capitalize())
    sub_mode = sub_mode_map.get(session.mode_config_id, None)
    
    # Build breadcrumb
    breadcrumb = f"{module_name} > {main_mode}"
    
    # Append sub-mode if it's distinct and defined
    if sub_mode and sub_mode.lower() != main_mode.lower():
        breadcrumb += f" > {sub_mode}"
    elif not sub_mode and session.mode_config_id and session.mode_config_id != session.learning_mode:
        # Fallback for unknown sub-modes
        breadcrumb += f" > {session.mode_config_id}"
        
    return breadcrumb

@blueprint.route('/api/active')
@login_required
def api_get_active_sessions():
    """Nhận danh sách các phiên học đang hoạt động của người dùng."""
    try:
        active_sessions = LearningSessionService.get_active_sessions(current_user.user_id)
        results = []
        for s in active_sessions:
            container_name = "Bộ học tập"
            try:
                if isinstance(s.set_id_data, int):
                    container = LearningContainer.query.get(s.set_id_data)
                    if container: 
                        container_name = container.title
                elif isinstance(s.set_id_data, list):
                    container_name = f"{len(s.set_id_data)} bộ học tập"
            except Exception as e:
                current_app.logger.warning(f"Error resolving container name: {e}")

            # Determine Resume URL based on learning mode
            resume_url = '#'
            mode = s.learning_mode
            
            if mode == 'quiz':
                resume_url = safe_url_for('quiz.quiz_session', session_id=s.session_id)
            elif mode == 'typing':
                resume_url = safe_url_for('vocab_typing.typing_session_page')
            elif mode == 'listening':
                # Ưu tiên module vocab_listening mới, fallback về vocabulary cũ nếu cần
                resume_url = safe_url_for('vocab_listening.listening_session_page')
                if resume_url == '#':
                     resume_url = safe_url_for('vocabulary.listening_session_page')
            elif mode == 'matching':
                sid = s.set_id_data
                if isinstance(sid, list): sid = sid[0] if sid else 0
                resume_url = safe_url_for('vocab_matching.matching_session_page', set_id=sid)
            elif mode == 'mcq':
                sid = s.set_id_data
                if isinstance(sid, list): sid = sid[0] if sid else 0
                resume_url = safe_url_for('vocab_mcq.mcq_session', set_id=sid)
            elif mode == 'speed':
                sid = s.set_id_data
                if isinstance(sid, list): sid = sid[0] if sid else 0
                resume_url = safe_url_for('vocab_speed.speed_session_page', set_id=sid)
            else:
                # Default to Flashcard
                resume_url = safe_url_for('vocab_flashcard.flashcard_session', session_id=s.session_id)

            results.append({
                'session_id': s.session_id,
                'learning_mode': s.learning_mode,
                'mode_name': get_mode_description(s),
                'container_name': container_name,
                'progress': {'done': len(s.processed_item_ids or []), 'total': s.total_items},
                'resume_url': resume_url
            })
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Error getting active sessions API: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@blueprint.route('/api/check_active/<int:set_id>')
@login_required
def check_active_vocab_session(set_id):
    """Kiểm tra xem có phiên nào đang active cho bộ thẻ này không."""
    try:
        active_session = LearningSessionService.get_any_active_vocabulary_session(current_user.user_id, set_id)
        if active_session:
            resume_url = '#'
            mode = active_session.learning_mode
            
            if mode == 'flashcard': 
                resume_url = safe_url_for('vocab_flashcard.flashcard_session', session_id=active_session.session_id)
            elif mode == 'mcq': 
                resume_url = safe_url_for('vocab_mcq.mcq_session', set_id=set_id)
            elif mode == 'typing': 
                resume_url = safe_url_for('vocab_typing.typing_session_page')
            elif mode == 'listening': 
                resume_url = safe_url_for('vocab_listening.listening_session_page')
            elif mode == 'matching':
                sid = set_id
                if isinstance(sid, list): sid = sid[0] if sid else 0
                resume_url = safe_url_for('vocab_matching.matching_session_page', set_id=sid)
            elif mode == 'speed':
                sid = set_id
                if isinstance(sid, list): sid = sid[0] if sid else 0
                resume_url = safe_url_for('vocab_speed.speed_session_page', set_id=sid)
            
            mode_names = {
                'flashcard': 'Từ vựng > Flashcard', 
                'mcq': 'Từ vựng > Trắc nghiệm (MCQ)', 
                'typing': 'Từ vựng > Gõ từ (Typing)', 
                'listening': 'Từ vựng > Luyện nghe', 
                'matching': 'Từ vựng > Nối từ', 
                'speed': 'Từ vựng > Ôn nhanh'
            }
            
            return jsonify({
                'has_active': True, 
                'active_mode': mode, 
                'active_mode_display': mode_names.get(mode, mode), 
                'resume_url': resume_url
            })
        return jsonify({'has_active': False})
    except Exception as e:
        current_app.logger.error(f"Error checking active session: {e}", exc_info=True)
        return jsonify({'has_active': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
# Unified Session Driver API
# ══════════════════════════════════════════════════════════════════════


@blueprint.route('/api/<int:session_id>/submit', methods=['POST'])
@login_required
def api_submit_answer(session_id):
    """
    Unified submission endpoint.

    POST /session/api/<session_id>/submit
    Payload: { "item_id": 123, "answer_index": 2, ... }

    Returns: { "item_id", "is_correct", "quality", "score_change",
               "feedback", "srs_update" }
    """
    try:
        user_input = request.get_json(silent=True) or {}

        # Security: ensure session belongs to current user
        session = LearningSessionService.get_session_by_id(session_id)
        if not session or session.user_id != current_user.user_id:
            return jsonify({'error': 'Session not found'}), 404

        result = LearningSessionService.submit_answer(session_id, user_input)
        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        return jsonify({'error': f'Driver not available: {e}'}), 422
    except Exception as e:
        current_app.logger.error(f"Error in submit_answer API: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@blueprint.route('/api/start', methods=['POST'])
@login_required
def api_start_driven_session():
    """
    Start a new session via the Driver Pattern.

    POST /session/api/start
    Payload: {
        "container_id": 42,
        "learning_mode": "mcq",
        "settings": { "num_choices": 4, "filter": "mixed" }
    }

    Returns: { "session_id", "total_items", "learning_mode" }
    """
    try:
        data = request.get_json(silent=True) or {}
        container_id = data.get('container_id')
        learning_mode = data.get('learning_mode', 'flashcard')
        settings = data.get('settings', {})

        if not container_id:
            return jsonify({'error': 'container_id is required'}), 400

        db_session, driver_state = LearningSessionService.start_driven_session(
            user_id=current_user.user_id,
            container_id=container_id,
            learning_mode=learning_mode,
            settings=settings,
        )

        if db_session is None:
            return jsonify({'error': 'Failed to create session'}), 500

        return jsonify({
            'session_id': db_session.session_id,
            'total_items': driver_state.total_items,
            'learning_mode': learning_mode,
            'item_queue_length': len(driver_state.item_queue),
        })

    except KeyError as e:
        return jsonify({'error': f'Driver not available: {e}'}), 422
    except Exception as e:
        current_app.logger.error(f"Error starting driven session: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@blueprint.route('/api/<int:session_id>/next')
@login_required
def api_get_next_interaction(session_id):
    """
    Get the next interaction for a session.

    GET /session/api/<session_id>/next

    Returns: InteractionPayload or { "finished": true }
    """
    try:
        from mindstack_app.modules.session.drivers.registry import DriverRegistry
        from mindstack_app.modules.session.drivers.base import SessionState

        session = LearningSessionService.get_session_by_id(session_id)
        if not session or session.user_id != current_user.user_id:
            return jsonify({'error': 'Session not found'}), 404
        if session.status != 'active':
            return jsonify({'error': 'Session is not active'}), 400

        # Resolve driver
        driver = DriverRegistry.resolve(session.learning_mode)

        # [FIX] Ensure we get fresh data (stats) from DB
        from mindstack_app.core.extensions import db
        db.session.expire_all()

        # Rebuild state from DB
        container_id = session.set_id_data if isinstance(session.set_id_data, int) else 0
        from mindstack_app.models import LearningItem
        
        # [FIX] Restore settings from session_data (persisted at session start)
        persisted_settings = {}
        if session.session_data and isinstance(session.session_data, dict):
            persisted_settings = session.session_data.get('settings', {})
        
        # [FIX] Handle dynamic SRS modes:
        # For dynamic modes (srs, mixed, due, new, etc.), keep queue EMPTY.
        # VocabularyDriver.get_next_interaction() will do a fresh FSRS query.
        DYNAMIC_FILTERS = {'srs', 'mixed', 'mixed_srs', 'due', 'new', 'review', 'available'}
        current_filter = persisted_settings.get('filter', '')
        
        if current_filter in DYNAMIC_FILTERS:
            # Dynamic mode: empty queue, let VocabularyDriver fetch on-demand
            all_item_ids = []
            current_app.logger.info(f"[SESSION_API] Dynamic SRS mode (filter={current_filter}). Queue kept empty for fresh FSRS query.")
        else:
            # Static mode: load persisted queue or fallback to all items
            stored_queue = None
            if session.session_data and isinstance(session.session_data, dict):
                stored_queue = session.session_data.get('item_queue')
                
            if stored_queue:
                current_app.logger.info(f"[SESSION_API] Using persisted queue of length {len(stored_queue)}")
                all_item_ids = stored_queue
            else:
                current_app.logger.warning(f"[SESSION_API] No persisted queue found. Loading ALL items (legacy).")
                all_item_ids = [
                    i.item_id for i in
                    LearningItem.query.filter_by(container_id=container_id)
                    .order_by(LearningItem.order_in_container.asc()).all()
                ]

        state = SessionState(
            user_id=session.user_id,
            container_id=container_id,
            mode=session.learning_mode,
            session_id=session_id,
            item_queue=all_item_ids,
            processed_ids=list(session.processed_item_ids or []),
            correct_count=session.correct_count or 0,
            incorrect_count=session.incorrect_count or 0,
            total_items=session.total_items or 0,
            started_at=session.start_time.isoformat() if session.start_time else '',
            settings=persisted_settings,
        )

        payload = driver.get_next_interaction(state)

        if payload is None:
            # Auto-complete when queue is exhausted
            LearningSessionService.complete_session(session_id)
            summary = driver.finalize_session(state)
            import dataclasses
            return jsonify({'finished': True, 'summary': dataclasses.asdict(summary)})

        import dataclasses
        resp_data = dataclasses.asdict(payload)
        
        # [DEBUG] Log the stats in the payload
        if 'data' in resp_data and 'initial_stats' in resp_data['data']:
            stats = resp_data['data']['initial_stats']
            current_app.logger.info(f"[API] Next Item {resp_data['item_id']} Stats: Reps={stats.get('repetitions')}, Streak={stats.get('current_streak')}")
            
        return jsonify(resp_data)

    except KeyError as e:
        return jsonify({'error': f'Driver not available: {e}'}), 422
    except Exception as e:
        current_app.logger.error(f"Error getting next interaction: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@blueprint.route('/api/<int:session_id>/cancel', methods=['POST'])
@login_required
def api_cancel_session(session_id):
    """Cancel a session by ID."""
    try:
        session = LearningSessionService.get_session_by_id(session_id)
        if not session or session.user_id != current_user.user_id:
            return jsonify({'error': 'Session not found'}), 404
        
        success = LearningSessionService.cancel_session(session_id)
        return jsonify({'success': success})
    except Exception as e:
        current_app.logger.error(f"Error cancelling session API: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@blueprint.route('/api/log/<int:log_id>/detail')
@login_required
def api_get_log_detail(log_id):
    """
    Get detailed view for a specific study log (History).
    Renders a modal template.
    """
    try:
        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        from mindstack_app.models import LearningItem
        from mindstack_app.utils.content_renderer import render_text_field

        # 1. Fetch Log via Interface
        log_data = LearningHistoryInterface.get_log(log_id)
        if not log_data or log_data['user_id'] != current_user.user_id:
            return "Log not found", 404

        # Wrap log_data in a simple namespace-like object for template compatibility if needed, 
        # or just pass the dict. The template uses dot notation which works for some things in Jinja 
        # but not all if it's a dict. However, Jinja allows dot notation for dict keys.
        log = log_data

        # 2. Fetch Item Content
        item = LearningItem.query.get(log['item_id'])
        item_content = "Item Deleted"
        correct_answer = None

        if item:
            # Render content based on type
            if item.item_type == 'FLASHCARD':
                item_content = render_text_field(item.content.get('front', ''), 'front')
                # NEW: Support BBCode for back
                correct_answer = render_text_field(item.content.get('back', ''), 'back')
            elif item.item_type == 'QUIZ':
                item_content = render_text_field(item.content.get('question', ''), 'question')
                # Determine correct answer from options
                correct_option_key = item.content.get('correct_option') # e.g. "option_1"
                options = item.content.get('options', {})
                if correct_option_key and options:
                     # NEW: Support BBCode for quiz options
                     correct_answer = render_text_field(options.get(correct_option_key), 'option')
            elif item.item_type == 'TYPING':
                 item_content = render_text_field(item.content.get('question', ''), 'question')
                 correct_answer = render_text_field(item.content.get('correct_answer'), 'correct_answer')
        
        # 3. Process User Answer with BBCode if available
        user_answer_rendered = log.get('user_answer')
        if log.get('user_answer'):
            # Heuristic: If it already looks like HTML (contains <...>), skip rendering to avoid double-escaping
            import re
            if not re.search(r'<[^>]+>', log.get('user_answer')):
                user_answer_rendered = render_text_field(log.get('user_answer'), 'user_answer')
            else:
                current_app.logger.info(f"[SESSION_API] Skipping BBCode render for Log {log_id}: HTML detected in answer.")

        # Calculate Score Fallback
        game_snapshot = log.get('gamification_snapshot') or {}
        score_change = game_snapshot.get('score_change', 0)
        
        if score_change == 0:
             # Fallback logic mirroring session_summary
             rating = log.get('rating')
             if rating == 3: score_change = 10
             elif rating == 4: score_change = 15
             elif rating == 2: score_change = 5

        # 4. Render Template
        return render_template('aura_mobile/modules/learning/modals/log_detail.html', 
                               log=log, 
                               item_content=item_content,
                               correct_answer=correct_answer,
                               score_change=score_change,
                               user_answer_rendered=user_answer_rendered)

    except Exception as e:
        current_app.logger.error(f"Error fetching log detail: {e}", exc_info=True)
        return f"Error: {e}", 500

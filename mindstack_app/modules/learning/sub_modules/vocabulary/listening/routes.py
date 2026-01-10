from flask import render_template, request, jsonify, abort, url_for
from flask_login import login_required, current_user

from . import listening_bp
from .logic import get_listening_eligible_items, check_listening_answer
from mindstack_app.models import LearningContainer
from mindstack_app.extensions import csrf_protect


@listening_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """Listening learning setup page - Wizard Style."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi Luyện nghe")
    
    # Get available keys
    from mindstack_app.modules.learning.sub_modules.vocabulary.mcq.logic import get_available_content_keys
    available_keys = get_available_content_keys(set_id)
    
    # Audio keys only (for question dropdown)
    audio_keys = [k for k in available_keys if 'audio' in k.lower()]
    
    # Calculate counts for each mode
    from mindstack_app.models import LearningItem, LearningProgress
    from datetime import datetime, timezone

    base_query = LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD')
    
    count_new = base_query.filter(~LearningItem.progress_records.any()).count()
    
    now = datetime.now(timezone.utc)
    count_review = base_query.join(LearningProgress).filter(LearningProgress.due_time <= now).count()
    count_learned = base_query.join(LearningProgress).count()
    count_hard = base_query.join(LearningProgress).filter(LearningProgress.easiness_factor < 2.5).count()
    count_random = len(items)

    # Load saved settings & defaults
    saved_settings = {}
    default_settings = {}

    if container.settings and container.settings.get('listening'):
        default_settings = container.settings.get('listening').copy()
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    try:
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('listening'):
            saved_settings = ucs.settings.get('listening', {})
    except Exception as e:
        pass

    return render_template(
        'v3/pages/learning/vocabulary/listening/setup/index.html',
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
        audio_keys=audio_keys,
        saved_settings=saved_settings,
        default_settings=default_settings
    )


@listening_bp.route('/start', methods=['POST'])
@login_required
def start_session():
    """Start a listening session: Save settings and redirect."""
    try:
        from flask import session
        from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService

        data = request.get_json()
        
        set_id = data.get('set_id')
        mode = data.get('mode', 'random')
        count = data.get('count', 10)
        use_custom_config = data.get('use_custom_config', False)
        custom_pairs = data.get('custom_pairs')
        
        if not set_id:
            return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        # Save to Session
        session['listening_session'] = {
            'set_id': set_id,
            'mode': mode,
            'count': count,
            'custom_pairs': custom_pairs
        }
        
        # Create DB Session
        try:
            db_session = LearningSessionService.create_session(
                user_id=current_user.user_id,
                learning_mode='listening',
                mode_config_id=mode,
                set_id_data=set_id,
                total_items=count if count else 0
            )
            if db_session:
                session['listening_session']['db_session_id'] = db_session.session_id
        except Exception as e:
            print(f"Error creating DB session for listening: {e}")

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
            if 'listening' not in new_settings: new_settings['listening'] = {}
            
            new_settings['listening']['mode'] = mode
            if count is not None:
                new_settings['listening']['count'] = int(count)
            else:
                new_settings['listening']['count'] = 10
            new_settings['listening']['use_custom_config'] = bool(use_custom_config)
            if custom_pairs:
                new_settings['listening']['custom_pairs'] = custom_pairs
            
            ucs.settings = new_settings
            flag_modified(ucs, "settings")
            safe_commit(db.session)
        except Exception as e:
            import traceback
            traceback.print_exc()
            
        return jsonify({
            'success': True, 
            'redirect_url': url_for('learning.vocabulary.listening.session_page')
        })
    except Exception as outer_e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f"Server Error: {str(outer_e)}"}), 500


@listening_bp.route('/session/')
@login_required
def session_page():
    """Listening learning session page (Clean URL)."""
    from flask import session, redirect
    
    session_data = session.get('listening_session', {})
    set_id = session_data.get('set_id')
    
    if not set_id:
        return redirect(url_for('learning.vocabulary.dashboard'))
        
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    custom_pairs = session_data.get('custom_pairs')
    count = session_data.get('count', 10)
    
    return render_template(
        'v3/pages/learning/vocabulary/listening/session/index.html',
        container=container,
        custom_pairs=custom_pairs,
        count=count
    )


@listening_bp.route('/session/<int:set_id>')
@login_required
def session(set_id):
    """Listening learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Get eligible items
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ có Audio để chơi Luyện nghe")
    
    # [UPDATED] Save settings to persistence
    try:
        count = request.args.get('count', 10, type=int)
        
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                settings={}
            )
            from mindstack_app.models import db
            db.session.add(ucs)
        
        # Update settings
        new_settings = dict(ucs.settings or {})
        if 'listening' not in new_settings: new_settings['listening'] = {}
        
        new_settings['listening']['count'] = count
        
        ucs.settings = new_settings
        from mindstack_app.utils.db_session import safe_commit
        from mindstack_app.models import db
        safe_commit(db.session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass

    return render_template(
        'v3/pages/learning/vocabulary/listening/session/index.html',
        container=container,
        total_items=len(items)
    )


@listening_bp.route('/setup/save/<int:set_id>', methods=['POST'])
@login_required
def save_setup(set_id):
    """API to save Listening settings."""
    try:
        data = request.get_json()
        count = data.get('count', 10)
        custom_pairs = data.get('custom_pairs')

        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        # Update settings
        new_settings = dict(ucs.settings or {})
        if 'listening' not in new_settings: new_settings['listening'] = {}
        
        new_settings['listening']['count'] = int(count) if count else 10
        if custom_pairs:
            new_settings['listening']['custom_pairs'] = custom_pairs
        
        ucs.settings = new_settings
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ucs, "settings")
        
        safe_commit(db.session)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@listening_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for a listening session. Returns text for TTS."""
    from flask import session, current_app
    
    current_app.logger.info(f"[Listening] api_get_items called for set_id={set_id}")
    
    # Priority: URL Args > Session > Defaults
    count = request.args.get('count', type=int)
    
    custom_pairs = None
    mode = 'random'
    
    # Try getting from session if set_id matches
    session_data = session.get('listening_session', {})
    if session_data.get('set_id') == set_id:
        if count is None: count = session_data.get('count')
        if session_data.get('custom_pairs'):
            custom_pairs = session_data.get('custom_pairs')
        mode = session_data.get('mode', 'random')

    # Fallback default
    if count is None: count = 10

    # Get Eligible Items with mode filtering
    items = get_listening_eligible_items(set_id, mode=mode)
    if len(items) < 1:
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected_raw = items if count <= 0 else items[:min(count, len(items))]
    
    # Remap based on Custom Pairs - return text for TTS
    final_items = []
    
    for item in selected_raw:
        content = item.get('content', {})
        
        # Determine config for this item
        pair = None
        if custom_pairs:
            pair = random.choice(custom_pairs)
        
        if pair:
            q_key = pair.get('q', 'front')  # Text column for TTS
            a_key = pair.get('a', 'back')   # Answer column
            
            question_text = content.get(q_key, '') or content.get('front', '')
            answer_text = content.get(a_key, '') or content.get('back', '')
            
            # Meaning: opposite of answer
            meaning = content.get('back', '') if a_key != 'back' else content.get('front', '')
            
            if (question_text or answer_text): # Allow if either is present
                final_items.append({
                    'item_id': item.get('item_id'),
                    'question_text': question_text or "No text",  # Final fallback 
                    'answer': answer_text or "No answer",
                    'meaning': meaning,
                    'content': content
                })
        else:
            # Default: front -> front (listen to front, type front)
            final_items.append({
                'item_id': item.get('item_id'),
                'question_text': content.get('front', ''),
                'answer': content.get('front', ''),
                'meaning': content.get('back', ''),
                'content': content
            })
    
    # Log first item for debugging
    if final_items:
        current_app.logger.info(f"[Listening] Returning {len(final_items)} items. First item question_text: {final_items[0].get('question_text', 'MISSING')[:50]}...")
    else:
        current_app.logger.warning("[Listening] No items found!")
            
    return jsonify({
        'success': True,
        'items': final_items,
        'total': len(final_items),
        'tts_url': url_for('learning.vocabulary.listening.api_tts', _external=True)
    })


@listening_bp.route('/api/check', methods=['POST'])
@login_required
@csrf_protect.exempt
def api_check_answer():
    """API to check typed answer."""
    from flask import session
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService

    data = request.get_json()
    correct_answer = data.get('correct_answer', '')
    user_answer = data.get('user_answer', '')
    duration_ms = data.get('duration_ms', 0)
    
    result = check_listening_answer(correct_answer, user_answer)
    result['user_answer'] = user_answer
    result['duration_ms'] = duration_ms
    
    # Update SRS using new Vocabulary Service
    item_id = data.get('item_id')
    if item_id:
        from mindstack_app.modules.learning.services.srs_service import SrsService
        from mindstack_app.utils.db_session import safe_commit
        from mindstack_app.models import db

        srs_result = SrsService.process_interaction(
            user_id=current_user.user_id,
            item_id=item_id,
            mode='listening',
            result_data=result
        )
        safe_commit(db.session)
        # Flatten srs_result into main response
        result.update(srs_result)
        
        # Update DB Session
        session_data = session.get('listening_session', {})
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


@listening_bp.route('/api/tts', methods=['GET', 'POST'])
@login_required
@csrf_protect.exempt
def api_tts():
    """API to get/generate TTS audio. 
    Supports GET (for direct audio src) and POST (for AJAX).
    If no language prefix, defaults to English.
    """
    import asyncio
    from flask import current_app, redirect, request, jsonify
    
    try:
        current_app.logger.info(f"[TTS] Request method: {request.method}")
        current_app.logger.info(f"[TTS] Request args: {request.args}")
        current_app.logger.info(f"[TTS] Request json: {request.get_json(silent=True)}")
        
        # Get text from either GET or POST
        if request.method == 'GET':
            text = request.args.get('text', '')
        else:
            data = request.get_json(silent=True) or {}
            text = data.get('text', '')
            
        if not text or not text.strip():
            current_app.logger.warning(f"[TTS] Validation failed: text is empty. Args: {request.args}, Data: {request.data}")
            return jsonify({
                'success': False, 
                'message': 'No text provided. If you see this, please hard refresh (Ctrl+F5).',
                'debug': {
                    'args': dict(request.args),
                    'method': request.method,
                    'has_json': bool(request.get_json(silent=True))
                }
            }), 400
        
        text = text.strip()
        
        # Default to English if no language prefix found (e.g. "vi:", "en:", "ja:")
        import re
        if not re.match(r'^[a-z]{2,3}:', text.lower()):
            text = f"en: {text}"
            
        from mindstack_app.modules.learning.sub_modules.flashcard.services.audio_service import AudioService
        audio_service = AudioService()
        
        # Run async generation in a sync wrapper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            path_or_url, success, msg = loop.run_until_complete(
                audio_service.get_cached_or_generate_audio(text)
            )
        finally:
            loop.close()
            
        if success and path_or_url:
            from flask import url_for
            from mindstack_app.config import Config
            import os
            
            # Resolve to absolute URL for frontend
            if path_or_url.startswith(('http://', 'https://')):
                audio_url = path_or_url
            else:
                # AudioService returns absolute paths like C:\...\uploads\flashcard\audio\cache\hash.mp3
                # We need to make it relative to UPLOAD_FOLDER (which is our static_folder)
                abs_path = os.path.abspath(path_or_url)
                rel_path = os.path.relpath(abs_path, Config.UPLOAD_FOLDER)
                
                # Convert backslashes to forward slashes for URLs
                rel_path = rel_path.replace('\\', '/')
                audio_url = url_for('static', filename=rel_path, _external=True)
            
            current_app.logger.info(f"[TTS] Success. Final audio_url: {audio_url}")
            
            # If it's a direct GET request (from <audio src="...">), just redirect to the file
            if request.method == 'GET':
                return redirect(audio_url)
            
            # For POST/AJAX, return JSON
            return jsonify({
                'success': True,
                'audio_url': audio_url
            })
        else:
            return jsonify({'success': False, 'message': msg or 'TTS failed'}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@listening_bp.route('/api/end_session', methods=['POST'])
@login_required
def end_session():
    """End the listening session."""
    from flask import session
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService

    try:
        session_data = session.get('listening_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            LearningSessionService.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# File: vocabulary/routes/listening.py
# Listening Learning Mode Routes

from flask import render_template, request, jsonify, abort, url_for, session, redirect
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import blueprint
from ..logics.listening_logic import get_listening_eligible_items, check_listening_answer
from mindstack_app.modules.vocab_mcq.logics.mcq_logic import get_available_content_keys
from mindstack_app.models import LearningContainer, UserContainerState, LearningItem, LearningProgress, db
from mindstack_app.core.extensions import csrf_protect
from mindstack_app.utils.db_session import safe_commit
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone

@blueprint.route('/listening/setup/<int:set_id>')
@login_required
def listening_setup(set_id):
    """Listening learning setup page - Wizard Style."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ để chơi Luyện nghe")
    
    available_keys = get_available_content_keys(set_id)
    audio_keys = [k for k in available_keys if 'audio' in k.lower()]
    
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

    if container.settings and container.settings.get('listening'):
        default_settings = container.settings.get('listening').copy()
        if 'pairs' in default_settings:
            default_settings['custom_pairs'] = default_settings.pop('pairs')

    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('listening'):
            saved_settings = ucs.settings.get('listening', {})
    except Exception as e:
        pass

    return render_dynamic_template('modules/learning/vocab_listening/setup/index.html',
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


@blueprint.route('/listening/start', methods=['POST'])
@login_required
def listening_start_session():
    """Start a listening session: Save settings and redirect."""
    try:
        from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService

        data = request.get_json()
        
        set_id = data.get('set_id')
        mode = data.get('mode', 'random')
        count = data.get('count', 10)
        use_custom_config = data.get('use_custom_config', False)
        custom_pairs = data.get('custom_pairs')
        
        if not set_id:
            return jsonify({'success': False, 'message': 'Missing set_id'}), 400

        session['listening_session'] = {
            'set_id': set_id,
            'mode': mode,
            'count': count,
            'custom_pairs': custom_pairs
        }
        
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

        try:
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
            'redirect_url': url_for('vocab_listening.listening_session_page')
        })
    except Exception as outer_e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f"Server Error: {str(outer_e)}"}), 500


@blueprint.route('/listening/session/')
@login_required
def listening_session_page():
    """Listening learning session page (Clean URL)."""
    session_data = session.get('listening_session', {})
    set_id = session_data.get('set_id')
    
    if not set_id:
        return redirect(url_for('vocabulary.dashboard_home'))
        
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    custom_pairs = session_data.get('custom_pairs')
    count = session_data.get('count', 10)
    
    return render_dynamic_template('modules/learning/vocab_listening/session/index.html',
        container=container,
        custom_pairs=custom_pairs,
        count=count
    )


@blueprint.route('/listening/session/<int:set_id>')
@login_required
def listening_session(set_id):
    """Listening learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        abort(400, description="Cần ít nhất 1 thẻ có Audio để chơi Luyện nghe")
    
    try:
        count = request.args.get('count', 10, type=int)
        
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                settings={}
            )
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'listening' not in new_settings: new_settings['listening'] = {}
        
        new_settings['listening']['count'] = count
        
        ucs.settings = new_settings
        safe_commit(db.session)
    except Exception as e:
        pass

    return render_dynamic_template('modules/learning/vocab_listening/session/index.html',
        container=container,
        total_items=len(items)
    )


@blueprint.route('/listening/setup/save/<int:set_id>', methods=['POST'])
@login_required
def listening_save_setup(set_id):
    """API to save Listening settings."""
    try:
        data = request.get_json()
        count = data.get('count', 10)
        custom_pairs = data.get('custom_pairs')

        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if not ucs:
            ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, settings={})
            db.session.add(ucs)
        
        new_settings = dict(ucs.settings or {})
        if 'listening' not in new_settings: new_settings['listening'] = {}
        
        new_settings['listening']['count'] = int(count) if count else 10
        if custom_pairs:
            new_settings['listening']['custom_pairs'] = custom_pairs
        
        ucs.settings = new_settings
        
        flag_modified(ucs, "settings")
        safe_commit(db.session)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@blueprint.route('/listening/api/items/<int:set_id>')
@login_required
def listening_api_get_items(set_id):
    """API to get items for a listening session."""
    from flask import current_app
    
    count = request.args.get('count', type=int)
    
    custom_pairs = None
    mode = 'random'
    
    session_data = session.get('listening_session', {})
    if session_data.get('set_id') == set_id:
        if count is None: count = session_data.get('count')
        if session_data.get('custom_pairs'):
            custom_pairs = session_data.get('custom_pairs')
        mode = session_data.get('mode', 'random')

    if count is None: count = 10

    items = get_listening_eligible_items(set_id, mode=mode)
    if len(items) < 1:
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    import random
    random.shuffle(items)
    selected_raw = items if count <= 0 else items[:min(count, len(items))]
    
    final_items = []
    
    for item in selected_raw:
        content = item.get('content', {})
        
        pair = None
        if custom_pairs:
            pair = random.choice(custom_pairs)
        
        if pair:
            q_key = pair.get('q', 'front')
            a_key = pair.get('a', 'back')
            
            question_text = content.get(q_key, '') or content.get('front', '')
            answer_text = content.get(a_key, '') or content.get('back', '')
            meaning = content.get('back', '') if a_key != 'back' else content.get('front', '')
            
            if (question_text or answer_text):
                final_items.append({
                    'item_id': item.get('item_id'),
                    'question_text': question_text or "No text",
                    'answer': answer_text or "No answer",
                    'meaning': meaning,
                    'content': content
                })
        else:
            final_items.append({
                'item_id': item.get('item_id'),
                'question_text': content.get('front', ''),
                'answer': content.get('front', ''),
                'meaning': content.get('back', ''),
                'content': content
            })
            
    return jsonify({
        'success': True,
        'items': final_items,
        'total': len(final_items),
        'tts_url': url_for('vocab_listening.listening_api_tts', _external=True)
    })


@blueprint.route('/listening/api/check', methods=['POST'])
@login_required
@csrf_protect.exempt
def listening_api_check_answer():
    """API to check typed answer."""
    from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService

    data = request.get_json()
    correct_answer = data.get('correct_answer', '')
    user_answer = data.get('user_answer', '')
    duration_ms = data.get('duration_ms', 0)
    
    result = check_listening_answer(correct_answer, user_answer)
    result['user_answer'] = user_answer
    result['duration_ms'] = duration_ms
    
    item_id = data.get('item_id')
    if item_id:
        from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
        from mindstack_app.models import db

        progress, srs_result = FsrsService.process_answer(
            user_id=current_user.user_id,
            item_id=item_id,
            quality=1,
            mode='listening',
            duration_ms=duration_ms,
            target_text=correct_answer,
            user_answer=user_answer
        )
        safe_commit(db.session)
        from dataclasses import asdict
        srs_result_dict = asdict(srs_result)
        srs_result_dict['next_due'] = srs_result.next_review.isoformat() if srs_result.next_review else None
        
        result.update(srs_result_dict)
        
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


@blueprint.route('/listening/api/tts', methods=['GET', 'POST'])
@login_required
@csrf_protect.exempt
def listening_api_tts():
    """API to get/generate TTS audio."""
    import asyncio
    from flask import current_app, redirect
    
    if request.method == 'GET':
        text = request.args.get('text', '')
    else:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        
    if not text or not text.strip():
        return jsonify({'success': False, 'message': 'No text provided'}), 400
    
    text = text.strip()
    
    import re
    if not re.match(r'^[a-z]{2,3}:', text.lower()):
        text = f"en: {text}"
        
    from mindstack_app.modules.vocab_flashcard.services.audio_service import AudioService
    audio_service = AudioService()
    
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
        from mindstack_app.core.config import Config
        import os
        
        if path_or_url.startswith(('http://', 'https://')):
            audio_url = path_or_url
        else:
            abs_path = os.path.abspath(path_or_url)
            rel_path = os.path.relpath(abs_path, Config.UPLOAD_FOLDER)
            rel_path = rel_path.replace('\\', '/')
            audio_url = url_for('media_uploads', filename=rel_path, _external=True)
            
        if request.method == 'GET':
            return redirect(audio_url)
        
        return jsonify({
            'success': True,
            'audio_url': audio_url
        })
    else:
        return jsonify({'success': False, 'message': msg or 'TTS failed'}), 500

@blueprint.route('/listening/api/end_session', methods=['POST'])
@login_required
def listening_end_session():
    """End the listening session."""
    from flask import session
    from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService

    try:
        session_data = session.get('listening_session', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            LearningSessionService.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

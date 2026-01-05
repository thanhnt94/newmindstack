# File: vocabulary/listening/routes.py
# Listening Learning Mode Routes

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import listening_bp
from .logic import get_listening_eligible_items, check_listening_answer
from mindstack_app.models import LearningContainer



@listening_bp.route('/setup/<int:set_id>')
@login_required
def setup(set_id):
    """Listening learning setup page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
        
    # Get total items for count selection
    items = get_listening_eligible_items(set_id)
    
    # [UPDATED] Load saved settings & defaults
    saved_settings = {}
    default_settings = {}

    # Defaults
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

    from mindstack_app.modules.learning.sub_modules.vocabulary.mcq.logic import get_available_content_keys
    available_keys = get_available_content_keys(set_id) 

    return render_template(
        'v3/pages/learning/vocabulary/listening/setup/default/index.html',
        container=container,
        total_items=len(items),
        available_keys=available_keys,
        saved_settings=saved_settings,
        default_settings=default_settings
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
        'v3/pages/learning/vocabulary/listening/session/default/index.html',
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
    """API to get items for a listening session."""
    count = request.args.get('count', 10, type=int)
    
    # 1. Load Settings for Custom Pairs
    custom_pairs = []
    try:
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings and ucs.settings.get('listening'):
             custom_pairs = ucs.settings.get('listening').get('custom_pairs', [])
    except: pass

    # 2. Get Eligible Items (Default)
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    # 3. Shuffle and Pick
    import random
    random.shuffle(items)
    selected_raw = items[:min(count, len(items))]
    
    # 4. Remap based on Custom Pairs
    final_items = []
    
    for item in selected_raw:
        # Determine config for this item
        pair = None
        if custom_pairs:
            pair = random.choice(custom_pairs)
        
        # If no custom pair, default behavior (Front Audio -> Front Text) is already in item,
        # but we might want to ensure consistency if logic.py changed.
        # logic.py returns: answer=front, audio=front_audio.
        
        if pair:
            q_key = pair.get('q', 'front')
            a_key = pair.get('a', 'front')
            
            # Map
            content = item.get('content', {})
            audio_url = content.get(f"{q_key}_audio_url")
            answer = content.get(a_key)
            
            # Meaning logic: if answer is front, meaning is back. If answer is back, meaning is front.
            meaning = content.get('back') if a_key != 'back' else content.get('front')
            
            # Validation: Must have audio and answer
            if audio_url and answer:
                item['audio_url'] = audio_url
                item['answer'] = answer
                item['meaning'] = meaning
                final_items.append(item)
        else:
            final_items.append(item)
            
    return jsonify({
        'success': True,
        'items': final_items,
        'total': len(final_items)
    })


@listening_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_answer():
    """API to check typed answer."""
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
        result['srs'] = srs_result
        
    return jsonify(result)

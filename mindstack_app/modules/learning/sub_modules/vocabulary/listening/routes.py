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
    
    # [UPDATED] Load saved settings
    saved_settings = {}
    try:
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings:
            saved_settings = ucs.settings.get('listening', {})
    except Exception as e:
        pass

    return render_template(
        'listening/setup/default/index.html',
        container=container,
        total_items=len(items),
        saved_settings=saved_settings
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
        from mindstack_app.modules.shared.utils.db_session import safe_commit
        from mindstack_app.models import db
        safe_commit(db.session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass
    
    return render_template(
        'listening/session/default/index.html',
        container=container,
        total_items=len(items)
    )


@listening_bp.route('/api/items/<int:set_id>')
@login_required
def api_get_items(set_id):
    """API to get items for a listening session."""
    count = request.args.get('count', 10, type=int)
    
    items = get_listening_eligible_items(set_id)
    if len(items) < 1:
        return jsonify({'success': False, 'message': 'No items available'}), 400
    
    # Shuffle and pick items
    import random
    random.shuffle(items)
    selected = items[:min(count, len(items))]
    
    return jsonify({
        'success': True,
        'items': selected,
        'total': len(selected)
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
        from mindstack_app.modules.shared.utils.db_session import safe_commit
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

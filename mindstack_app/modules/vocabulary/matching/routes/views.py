# File: vocabulary/routes/matching.py
# Matching Learning Mode Routes

from flask import render_template, request, jsonify, abort, session
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from .. import matching_bp as blueprint
from ..logics.matching_logic import generate_matching_game
from mindstack_app.models import LearningContainer, LearningItem, db
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.core.signals import card_reviewed

@blueprint.route('/matching/session/<int:set_id>')
@login_required
def matching_session_page(set_id):
    """Matching learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    game_data = generate_matching_game(set_id, count=6)
    
    if not game_data:
        abort(400, description="Cần ít nhất 4 thẻ để chơi ghép đôi")
    
    from mindstack_app.modules.session.interface import SessionInterface
    db_session_id = None
    try:
        db_session = SessionInterface.create_session(
            user_id=current_user.user_id,
            learning_mode='matching',
            mode_config_id='matching_game',
            set_id_data=set_id,
            total_items=6
        )
        if db_session:
            db_session_id = db_session.session_id
    except Exception as e:
        print(f"Error creating DB session for matching: {e}")

    session['matching_game'] = {
        'set_id': set_id,
        'pairs': game_data['pairs'],
        'db_session_id': db_session_id
    }
    
    return render_dynamic_template('modules/learning/vocab_matching/session/index.html',
        container=container,
        game=game_data
    )


@blueprint.route('/matching/api/new-game/<int:set_id>')
@login_required
def matching_api_new_game(set_id):
    """API to generate a new matching game."""
    count = request.args.get('count', 6, type=int)
    
    game_data = generate_matching_game(set_id, count)
    
    if not game_data:
        return jsonify({'success': False, 'message': 'Not enough items'}), 400
    
    from mindstack_app.modules.session.interface import SessionInterface
    db_session_id = None
    try:
        db_session = SessionInterface.create_session(
            user_id=current_user.user_id,
            learning_mode='matching',
            mode_config_id='matching_game',
            set_id_data=set_id,
            total_items=count
        )
        if db_session:
            db_session_id = db_session.session_id
    except Exception as e:
        print(f"Error creating DB session for matching: {e}")

    session['matching_game'] = {
        'set_id': set_id,
        'pairs': game_data['pairs'],
        'db_session_id': db_session_id
    }
    
    return jsonify({
        'success': True,
        'game': {
            'left': game_data['left'],
            'right': game_data['right'],
            'total': game_data['total']
        }
    })


@blueprint.route('/matching/api/check', methods=['POST'])
@login_required
def matching_api_check_match():
    """API to check if a match is correct."""
    from mindstack_app.modules.session.interface import SessionInterface

    data = request.get_json()
    left_item_id = data.get('left_item_id')
    right_item_id = data.get('right_item_id')
    duration_ms = data.get('duration_ms', 0)
    user_answer = data.get('user_answer')
    
    is_correct = left_item_id == right_item_id
    
    from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
    from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
    
    srs_results = []
    
    def _process_match_item(item_id, correct, score_points=0):
        if not item_id: return
        
        fsrs_quality = 3 if correct else 1
        
        # [REMOVED] FSRS update as requested
        
        # [EMIT] Signal
        try:
            item = LearningItem.query.get(item_id)
            item_type = item.item_type if item else 'FLASHCARD'
            card_reviewed.send(
                None,
                user_id=current_user.user_id,
                item_id=item_id,
                quality=fsrs_quality,
                is_correct=correct,
                learning_mode='matching',
                score_points=score_points,
                item_type=item_type,
                reason=f"Vocab Matching Practice {'Correct' if correct else 'Incorrect'}"
            )
        except: pass
        
        # [LOG] History
        try:
            LearningHistoryInterface.record_log(
                user_id=current_user.user_id,
                item_id=item_id,
                result_data={
                    'rating': fsrs_quality,
                    'user_answer': user_answer,
                    'is_correct': correct,
                    'review_duration': duration_ms
                },
                context_data={
                    'session_id': session.get('matching_game', {}).get('db_session_id'),
                    'container_id': session.get('matching_game', {}).get('set_id'),
                    'learning_mode': 'matching'
                },
                game_snapshot={'score_earned': score_points}
            )
        except: pass
        
        return {'success': True}

    if is_correct:
         _process_match_item(left_item_id, True, score_points=10)
    else:
        _process_match_item(left_item_id, False, score_points=0)
        _process_match_item(right_item_id, False, score_points=0)
    
    safe_commit(db.session)

    session_data = session.get('matching_game', {})
    db_session_id = session_data.get('db_session_id')
    
    if db_session_id and is_correct:
        SessionInterface.update_progress(
            session_id=db_session_id,
            item_id=left_item_id,
            result_type='correct',
            points=10
        )
        
    return jsonify({
        'correct': is_correct,
        'updated_total_score': current_user.total_score
    })

@blueprint.route('/matching/api/end_session', methods=['POST'])
@login_required
def matching_end_session():
    """End the matching session."""
    from mindstack_app.modules.session.interface import SessionInterface
    
    try:
        session_data = session.get('matching_game', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            SessionInterface.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

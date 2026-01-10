# File: vocabulary/matching/routes.py
# Matching Learning Mode Routes

from flask import render_template, request, jsonify, abort, session
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from . import matching_bp
from .logic import generate_matching_game
from mindstack_app.models import LearningContainer


@matching_bp.route('/session/<int:set_id>')
@login_required
def session_page(set_id):
    """Matching learning session page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Generate game
    game_data = generate_matching_game(set_id, count=6)
    
    if not game_data:
        abort(400, description="Cần ít nhất 4 thẻ để chơi ghép đôi")
    
    # Create DB Session
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService
    db_session_id = None
    try:
        # Matching doesn't have a fixed total_items in the same way, but let's assume 'count' is the pair count
        db_session = LearningSessionService.create_session(
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

    # Store correct pairs in session for validation
    session['matching_game'] = {
        'set_id': set_id,
        'pairs': game_data['pairs'],
        'db_session_id': db_session_id
    }
    
    return render_dynamic_template('pages/learning/vocabulary/matching/session/index.html',
        container=container,
        game=game_data
    )


@matching_bp.route('/api/new-game/<int:set_id>')
@login_required
def api_new_game(set_id):
    """API to generate a new matching game."""
    count = request.args.get('count', 6, type=int)
    
    game_data = generate_matching_game(set_id, count)
    
    if not game_data:
        return jsonify({'success': False, 'message': 'Not enough items'}), 400
    
    # Create DB Session
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService
    db_session_id = None
    try:
        db_session = LearningSessionService.create_session(
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

    # Store in session
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


@matching_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_match():
    """API to check if a match is correct."""
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService

    data = request.get_json()
    left_item_id = data.get('left_item_id')
    right_item_id = data.get('right_item_id')
    duration_ms = data.get('duration_ms', 0)
    user_answer = data.get('user_answer')
    
    # Check if item_ids match (same item = correct pair)
    is_correct = left_item_id == right_item_id
    
    # SRS Update
    from mindstack_app.modules.learning.services.srs_service import SrsService
    from mindstack_app.utils.db_session import safe_commit
    from mindstack_app.models import db
    
    srs_results = []
    
    if is_correct:
         # Correct: Update the item (left_item_id is same as right)
         srs = SrsService.process_interaction(
             user_id=current_user.user_id,
             item_id=left_item_id,
             mode='matching',
             result_data={'is_correct': True, 'duration_ms': duration_ms, 'user_answer': user_answer}
         )
         srs_results.append(srs)
    else:
        # Incorrect: Penalty for BOTH items involved in confusion
        # We process them individually
        if left_item_id:
             SrsService.process_interaction(
                 user_id=current_user.user_id,
                 item_id=left_item_id,
                 mode='matching',
                 result_data={'is_correct': False, 'duration_ms': duration_ms, 'user_answer': user_answer}
             )
        if right_item_id:
             SrsService.process_interaction(
                 user_id=current_user.user_id,
                 item_id=right_item_id,
                 mode='matching',
                 result_data={'is_correct': False, 'duration_ms': duration_ms, 'user_answer': user_answer}
             )
    
    safe_commit(db.session)

    # Update DB Session
    session_data = session.get('matching_game', {})
    db_session_id = session_data.get('db_session_id')
    
    if db_session_id and is_correct:
        # Matching: only track correct matches as 'processed'
        LearningSessionService.update_progress(
            session_id=db_session_id,
            item_id=left_item_id,
            result_type='correct',
            points=10
        )
        
        # Check if game complete (simple check: if processed count matches total)
        # However, matching game logic is stateless in DB session service. 
        # Ideally we check stored session progress.
        
    return jsonify({
        'correct': is_correct,
        'srs': srs_results
    })

@matching_bp.route('/api/end_session', methods=['POST'])
@login_required
def end_session():
    """End the matching session."""
    from flask import session
    from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService
    
    try:
        session_data = session.get('matching_game', {})
        db_session_id = session_data.get('db_session_id')
        
        if db_session_id:
            LearningSessionService.complete_session(db_session_id)
            return jsonify({'success': True, 'session_id': db_session_id})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

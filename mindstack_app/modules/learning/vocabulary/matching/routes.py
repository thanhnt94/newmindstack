# File: vocabulary/matching/routes.py
# Matching Learning Mode Routes

from flask import render_template, request, jsonify, abort, session
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
    
    # Store correct pairs in session for validation
    session['matching_game'] = {
        'set_id': set_id,
        'pairs': game_data['pairs']
    }
    
    return render_template(
        'matching/session.html',
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
    
    # Store in session
    session['matching_game'] = {
        'set_id': set_id,
        'pairs': game_data['pairs']
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
    data = request.get_json()
    left_item_id = data.get('left_item_id')
    right_item_id = data.get('right_item_id')
    
    # Check if item_ids match (same item = correct pair)
    is_correct = left_item_id == right_item_id
    
    return jsonify({
        'correct': is_correct
    })

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mindstack_app.modules.fsrs.services.scheduler_service import SchedulerService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from mindstack_app.modules.fsrs.exceptions import FSRSError, CardNotDueError, InvalidRatingError

api_bp = Blueprint('fsrs_api', __name__, url_prefix='/api/fsrs')

@api_bp.route('/review', methods=['POST'])
@login_required
def process_review():
    """
    Process a card review.
    Input: {
        "item_id": int,
        "rating": int (1-4),
        "duration_ms": int,
        "mode": str (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    item_id = data.get('item_id')
    rating = data.get('rating')
    
    if not item_id or not rating:
        return jsonify({'error': 'item_id and rating are required'}), 400

    try:
        # Delegate to SchedulerService
        item_state, result = SchedulerService.process_review(
            user_id=current_user.user_id,
            item_id=item_id,
            quality=rating,
            mode=data.get('mode', 'flashcard'),
            duration_ms=data.get('duration_ms', 0)
        )
        
        return jsonify({
            'message': 'Review processed successfully',
            'data': {
                'next_review': result.next_review.isoformat(),
                'interval_minutes': result.interval_minutes,
                'state': result.state,
                'retrievability': round(result.retrievability * 100, 1),
                'stability': round(result.stability, 2),
                'difficulty': round(result.difficulty, 2)
            }
        }), 200

    except InvalidRatingError as e:
        return jsonify({'error': str(e)}), 400
    except CardNotDueError as e:
        return jsonify({'error': str(e)}), 400
    except FSRSError as e:
        return jsonify({'error': f"FSRS Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500


@api_bp.route('/preview/<int:item_id>', methods=['GET'])
@login_required
def preview_intervals(item_id):
    """
    Get preview intervals for a specific item.
    Output: { "1": {...}, "2": {...}, ... }
    """
    try:
        previews = SchedulerService.get_preview_intervals(current_user.user_id, item_id)
        return jsonify({
            'item_id': item_id,
            'previews': previews
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/train', methods=['POST'])
@login_required
def train_parameters():
    """
    Trigger FSRS optimization training for the current user.
    """
    try:
        params = FSRSOptimizerService.train_for_user(current_user.user_id)
        if params:
            return jsonify({
                'message': 'Optimization successful',
                'parameters': params
            }), 200
        else:
            return jsonify({
                'message': 'Optimization skipped (not enough data or check logs)',
                'parameters': None
            }), 200 # Not an error, just no update
    except Exception as e:
        return jsonify({'error': str(e)}), 500

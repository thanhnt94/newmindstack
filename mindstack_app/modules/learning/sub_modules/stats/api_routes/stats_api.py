"""
Stats REST API Routes

Provides REST API endpoints for Memory Power statistics.
Used by frontend for real-time stats display and dashboard analytics.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from mindstack_app.modules.learning.services.srs_service import SrsService
from mindstack_app.modules.learning.services.progress_service import ProgressService
from mindstack_app.models.learning_progress import LearningProgress


stats_api_bp = Blueprint('stats_api', __name__, url_prefix='/api/learning/stats')


@stats_api_bp.route('/item/<int:item_id>', methods=['GET'])
@login_required
def get_item_stats(item_id):
    """
    Get Memory Power statistics for a single item.
    
    Returns:
        {
            "mastery": 85.3,
            "retention": 92.1,
            "memory_power": 78.5,
            "next_review": "2025-12-31T10:00:00Z",
            "is_due": false,
            "status": "reviewing",
            "correct_streak": 5,
            "incorrect_streak": 0
        }
    """
    # Get mode from query param (default: flashcard)
    mode = request.args.get('mode', 'flashcard')
    
    # Fetch progress record
    progress = LearningProgress.query.filter_by(
        user_id=current_user.user_id,
        item_id=item_id,
        learning_mode=mode
    ).first()
    
    if not progress:
        return jsonify({
            'error': 'No progress found for this item',
            'mastery': 0,
            'retention': 0,
            'memory_power': 0,
            'is_due': True,
            'status': 'new'
        }), 404
    
    # Get real-time stats using SrsService
    stats = SrsService.get_item_stats(progress)
    
    # Add extra fields
    stats['correct_streak'] = progress.correct_streak or 0
    stats['incorrect_streak'] = progress.incorrect_streak or 0
    stats['next_review'] = progress.due_time.isoformat() if progress.due_time else None
    
    # Convert to percentages (0-100)
    stats['mastery'] = round(stats['mastery'] * 100, 1)
    stats['retention'] = round(stats['retention'] * 100, 1)
    stats['memory_power'] = round(stats['memory_power'] * 100, 1)
    
    # Add chart data for history
    review_history = SrsService.get_item_review_history(
        item_id=item_id,
        user_id=current_user.user_id,
        limit=50
    )
    
    stats['chart_data'] = {
        'memory_power_timeline': review_history,
        'review_count': len(review_history)
    }
    
    return jsonify(stats)


@stats_api_bp.route('/container/<int:container_id>', methods=['GET'])
@login_required
def get_container_stats(container_id):
    """
    Get aggregate statistics for a container (flashcard set, quiz, etc).
    
    Returns:
        {
            "total_items": 500,
            "average_memory_power": 72.5,
            "strong_items": 156,    // 80-100%
            "medium_items": 278,    // 50-80%
            "weak_items": 66,       // 0-50%
            "due_items": 45
        }
    """
    mode = request.args.get('mode', 'flashcard')
    
    # Use SrsService to get aggregate stats
    stats = SrsService.get_container_stats(
        user_id=current_user.user_id,
        container_id=container_id,
        mode=mode
    )
    
    # Convert average to percentage
    stats['average_memory_power'] = round(stats['average_memory_power'] * 100, 1)
    
    # Add chart data for timeline
    history = SrsService.get_container_history(
        user_id=current_user.user_id,
        container_id=container_id,
        days=30,
        mode=mode
    )
    
    stats['chart_data'] = {
        'timeline': history,
        'distribution': {
            'strong': stats['strong_items'],
            'medium': stats['medium_items'],
            'weak': stats['weak_items']
        }
    }
    
    return jsonify(stats)


@stats_api_bp.route('/batch', methods=['POST'])
@login_required
def get_batch_stats():
    """
    Get stats for multiple items at once.
    
    Request body:
        {
            "item_ids": [1, 2, 3, ...],
            "mode": "flashcard"  // optional
        }
    
    Returns:
        {
            "items": [
                {"item_id": 1, "mastery": 85.3, "retention": 92.1, ...},
                {"item_id": 2, "mastery": 60.2, "retention": 75.0, ...}
            ]
        }
    """
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    mode = data.get('mode', 'flashcard')
    
    if not item_ids:
        return jsonify({'error': 'No item_ids provided'}), 400
    
    # Fetch all progress records
    progress_records = LearningProgress.query.filter(
        LearningProgress.user_id == current_user.user_id,
        LearningProgress.item_id.in_(item_ids),
        LearningProgress.learning_mode == mode
    ).all()
    
    # Calculate stats for each
    results = []
    for progress in progress_records:
        stats = SrsService.get_item_stats(progress)
        stats['item_id'] = progress.item_id
        stats['correct_streak'] = progress.correct_streak or 0
        stats['incorrect_streak'] = progress.incorrect_streak or 0
        
        # Convert to percentages
        stats['mastery'] = round(stats['mastery'] * 100, 1)
        stats['retention'] = round(stats['retention'] * 100, 1)
        stats['memory_power'] = round(stats['memory_power'] * 100, 1)
        
        results.append(stats)
    
    return jsonify({'items': results})


@stats_api_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard_stats():
    """
    Get overall learning statistics for dashboard.
    
    Returns:
        {
            "total_items_studied": 1500,
            "average_memory_power": 68.5,
            "due_today": 45,
            "containers": [
                {
                    "container_id": 1,
                    "name": "TOEIC Vocabulary",
                    "average_memory_power": 72.5,
                    "total_items": 500,
                    "due_items": 12
                }
            ]
        }
    """
    from mindstack_app.models import LearningContainer
    
    mode = request.args.get('mode', 'flashcard')
    
    # Get all progress for user
    all_progress = LearningProgress.query.filter_by(
        user_id=current_user.user_id,
        learning_mode=mode
    ).all()
    
    if not all_progress:
        return jsonify({
            'total_items_studied': 0,
            'average_memory_power': 0,
            'due_today': 0,
            'containers': []
        })
    
    # Overall stats
    from mindstack_app.modules.learning.logics.unified_srs import UnifiedSrsSystem
    overall_stats = UnifiedSrsSystem.calculate_batch_stats(all_progress)
    
    # Group by container
    from collections import defaultdict
    container_groups = defaultdict(list)
    for p in all_progress:
        container_groups[p.item.container_id].append(p)
    
    # Calculate per-container stats
    containers = []
    for container_id, progress_list in container_groups.items():
        container = LearningContainer.query.get(container_id)
        if not container:
            continue
        
        container_stats = UnifiedSrsSystem.calculate_batch_stats(progress_list)
        containers.append({
            'container_id': container_id,
            'name': container.title,
            'average_memory_power': round(container_stats['average_memory_power'] * 100, 1),
            'total_items': container_stats['total_items'],
            'due_items': container_stats['due_items'],
            'strong_items': container_stats['strong_items'],
            'medium_items': container_stats['medium_items'],
            'weak_items': container_stats['weak_items']
        })
    
    return jsonify({
        'total_items_studied': overall_stats['total_items'],
        'average_memory_power': round(overall_stats['average_memory_power'] * 100, 1),
        'due_today': overall_stats['due_items'],
        'strong_items': overall_stats['strong_items'],
        'medium_items': overall_stats['medium_items'],
        'weak_items': overall_stats['weak_items'],
        'containers': containers
    })

from flask import jsonify, request
from flask_login import login_required, current_user
from mindstack_app.modules.learning.services.fsrs_service import FsrsService
from mindstack_app.modules.learning.services.progress_service import ProgressService
from mindstack_app.models.learning_progress import LearningProgress
from .. import stats_bp

@stats_bp.route('/api/memory/item/<int:item_id>', methods=['GET'])
@login_required
def get_memory_item_stats(item_id):
    """
    Get Memory Power statistics for a single item.
    Replaces /api/learning/stats/item/<id>
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
    
    # Get real-time stats using FsrsService
    stats = FsrsService.get_item_stats(progress)
    
    # Add extra fields
    stats['correct_streak'] = progress.correct_streak or 0
    stats['incorrect_streak'] = progress.incorrect_streak or 0
    stats['next_review'] = progress.fsrs_due.isoformat() if progress.fsrs_due else None
    
    # Convert to percentages (0-100)
    # Note: get_item_stats returns stability, difficulty, retrievability, is_due, state
    stats['retention'] = round(stats['retrievability'] * 100, 1)
    # 'memory_power' is now mapped to retention for compatibility
    stats['memory_power'] = stats['retention']
    # 'mastery' logic (optional, keeping stability as proxy)
    stats['mastery'] = round(min(100, (stats['stability'] / 21.0) * 100), 1)
    
    # Add chart data for history
    review_history = FsrsService.get_item_review_history(
        item_id=item_id,
        user_id=current_user.user_id,
        limit=50
    ) if hasattr(FsrsService, 'get_item_review_history') else []
    
    stats['chart_data'] = {
        'memory_power_timeline': review_history,
        'review_count': len(review_history)
    }
    
    return jsonify(stats)


@stats_bp.route('/api/memory/container/<int:container_id>', methods=['GET'])
@login_required
def get_memory_container_stats(container_id):
    """
    Get aggregate statistics for a container (flashcard set, quiz, etc).
    Replaces /api/learning/stats/container/<id>
    """
    mode = request.args.get('mode', 'flashcard')
    
    # Get all progress for this container
    from mindstack_app.models import LearningItem
    progress_records = LearningProgress.query.join(LearningItem).filter(
        LearningProgress.user_id == current_user.user_id,
        LearningItem.container_id == container_id,
        LearningProgress.learning_mode == mode
    ).all()

    # Use FsrsService to get aggregate stats
    stats = FsrsService.calculate_batch_stats(progress_records)
    
    # Convert average to percentage
    stats['average_memory_power'] = round(stats['average_retrievability'] * 100, 1)
    
    # Add chart data for timeline
    history = FsrsService.get_container_history(
        user_id=current_user.user_id,
        container_id=container_id,
        days=30,
        mode=mode
    ) if hasattr(FsrsService, 'get_container_history') else []
    
    stats['chart_data'] = {
        'timeline': history,
        'distribution': {
            'strong': stats['strong_items'],
            'medium': stats['medium_items'],
            'weak': stats['weak_items']
        }
    }
    
    return jsonify(stats)


@stats_bp.route('/api/memory/batch', methods=['POST'])
@login_required
def get_memory_batch_stats():
    """
    Get stats for multiple items at once.
    Replaces /api/learning/stats/batch
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
        stats = FsrsService.get_item_stats(progress)
        stats['item_id'] = progress.item_id
        stats['correct_streak'] = progress.correct_streak or 0
        stats['incorrect_streak'] = progress.incorrect_streak or 0
        
        # Convert to percentages
        stats['retention'] = round(stats['retrievability'] * 100, 1)
        stats['memory_power'] = stats['retention']
        
        results.append(stats)
    
    return jsonify({'items': results})


@stats_bp.route('/api/memory/dashboard', methods=['GET'])
@login_required
def get_memory_dashboard_stats():
    """
    Get overall learning statistics for dashboard (Memory Power focus).
    Replaces /api/learning/stats/dashboard
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
    overall_stats = FsrsService.calculate_batch_stats(all_progress)
    
    # Group by container
    from collections import defaultdict
    container_groups = defaultdict(list)
    for p in all_progress:
        # Check if item points to a container
        if p.item:
            container_groups[p.item.container_id].append(p)
    
    # Calculate per-container stats
    containers = []
    for container_id, progress_list in container_groups.items():
        container = LearningContainer.query.get(container_id)
        if not container:
            continue
        
        container_stats = FsrsService.calculate_batch_stats(progress_list)
        containers.append({
            'container_id': container_id,
            'name': container.title,
            'average_memory_power': round(container_stats['average_retrievability'] * 100, 1),
            'total_items': container_stats['total_items'],
            'due_items': container_stats['due_items'],
            'strong_items': container_stats['strong_items'],
            'medium_items': container_stats['medium_items'],
            'weak_items': container_stats['weak_items']
        })
    
    return jsonify({
        'total_items_studied': overall_stats['total_items'],
        'average_memory_power': round(overall_stats['average_retrievability'] * 100, 1),
        'due_today': overall_stats['due_items'],
        'strong_items': overall_stats['strong_items'],
        'medium_items': overall_stats['medium_items'],
        'weak_items': overall_stats['weak_items'],
        'containers': containers
    })

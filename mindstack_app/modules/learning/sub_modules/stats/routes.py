"""
Stats Module Routes

Provides dashboard page and data endpoints for learning analytics.
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from mindstack_app.modules.learning.services.srs_service import SrsService
from mindstack_app.models.learning_progress import LearningProgress
from mindstack_app.models import LearningContainer

# Import API routes
from .api_routes import stats_api_bp


# Main stats blueprint  
stats_bp = Blueprint('stats', __name__, 
                    url_prefix='/stats',
                    template_folder='templates')

# Note: stats_api_bp is registered separately in learning/routes.py
# because it has its own complete URL prefix (/api/learning/stats)


@stats_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page showing learning analytics."""
    mode = request.args.get('mode', 'flashcard')
    
    return render_template(
        'stats/dashboard/default/index.html',
        mode=mode
    )


@stats_bp.route('/dashboard/data')
@login_required
def dashboard_data():
    """API endpoint for dashboard data (called by JavaScript)."""
    mode = request.args.get('mode', 'flashcard')
    
    # Get all progress for user in this mode
    all_progress = LearningProgress.query.filter_by(
        user_id=current_user.user_id,
        learning_mode=mode
    ).all()
    
    if not all_progress:
        return jsonify({
            'total_items': 0,
            'average_memory_power': 0,
            'due_items': 0,
            'containers': []
        })
    
    # Calculate overall stats
    from mindstack_app.modules.learning.logics.unified_srs import UnifiedSrsSystem
    overall_stats = UnifiedSrsSystem.calculate_batch_stats(all_progress)
    
    # Group by container
    from collections import defaultdict
    container_groups = defaultdict(list)
    for p in all_progress:
        if p.item:
            container_groups[p.item.container_id].append(p)
    
    # Calculate per-container stats
    containers = []
    for container_id, progress_list in container_groups.items():
        container = LearningContainer.query.get(container_id)
        if not container:
            continue
        
        container_stats = UnifiedSrsSystem.calculate_batch_stats(progress_list)
        containers.append({
            'id': container_id,
            'title': container.title,
            'description': container.description or '',
            'average_memory_power': round(container_stats['average_memory_power'] * 100, 1),
            'total_items': container_stats['total_items'],
            'due_items': container_stats['due_items'],
            'strong_items': container_stats['strong_items'],
            'medium_items': container_stats['medium_items'],
            'weak_items': container_stats['weak_items']
        })
    
    # Sort by average memory power (best first)
    containers.sort(key=lambda x: x['average_memory_power'], reverse=True)
    
    return jsonify({
        'total_items': overall_stats['total_items'],
        'average_memory_power': round(overall_stats['average_memory_power'] * 100, 1),
        'due_items': overall_stats['due_items'],
        'strong_items': overall_stats['strong_items'],
        'medium_items': overall_stats['medium_items'],
        'weak_items': overall_stats['weak_items'],
        'containers': containers
    })

from flask import jsonify, request
from flask_login import login_required, current_user
from ..services.leaderboard_service import LeaderboardService
from .. import blueprint as stats_bp

@stats_bp.route('/api/leaderboard')
@login_required
def get_leaderboard_api():
    """Endpoint API cho bảng xếp hạng."""
    timeframe = request.args.get('timeframe', 'week')
    data = LeaderboardService.get_leaderboard(timeframe=timeframe, viewer_user=current_user)
    return jsonify({
        'success': True,
        'data': data
    })

@stats_bp.route('/api/leaderboard/container/<int:container_id>')
@login_required
def get_container_leaderboard_api(container_id):
    """Endpoint API cho bảng xếp hạng của một bộ thẻ."""
    timeframe = request.args.get('timeframe', 'all')
    from ..services.vocabulary_stats_service import VocabularyStatsService
    data = VocabularyStatsService.get_container_leaderboard(container_id, timeframe=timeframe)
    return jsonify({
        'success': True,
        'data': data
    })

@stats_bp.route('/api/summary')
@login_required
def api_get_stats_summary():
    """
    Get unified dashboard statistics from all modules.
    
    Uses StatsAggregator to fetch data via interfaces (not direct DB queries).
    Returns aggregated stats from FSRS, Gamification, and Activity modules.
    """
    from ..services.stats_aggregator import StatsAggregator
    
    try:
        data = StatsAggregator.get_user_dashboard_stats(current_user.user_id)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@stats_bp.route('/api/container/<int:container_id>/summary')
@login_required
def api_get_container_summary(container_id):
    """
    Get stats summary for a specific container.
    
    Uses StatsAggregator to fetch FSRS stats via interface.
    """
    from ..services.stats_aggregator import StatsAggregator
    
    try:
        data = StatsAggregator.get_container_summary(current_user.user_id, container_id)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


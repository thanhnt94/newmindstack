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

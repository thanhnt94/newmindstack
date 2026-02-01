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

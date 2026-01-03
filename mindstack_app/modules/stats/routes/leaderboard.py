from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from .. import stats_bp
from mindstack_app.modules.gamification.services.scoring_service import ScoreService

@stats_bp.route('/history')
@login_required
def score_history():
    """Trang lịch sử điểm thưởng của người dùng."""
    # Template will be moved to analytics/gamification/
    return render_template('v3/pages/analytics/gamification/score_history.html')

@stats_bp.route('/api/history', methods=['GET'])
@login_required
def get_score_history_api():
    """API lấy lịch sử điểm thưởng."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs, total = ScoreService.get_score_history(current_user.user_id, page, per_page)
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs],
        'total': total,
        'page': page,
        'per_page': per_page
    })

@stats_bp.route('/leaderboard')
@login_required
def leaderboard_ui():
    """Trang bảng xếp hạng (Gamification View)."""
    return render_template('v3/pages/analytics/gamification/leaderboard.html')

@stats_bp.route('/api/leaderboard', methods=['GET'])
@login_required
def get_gamification_leaderboard_api():
    """API lấy dữ liệu bảng xếp hạng (Gamification API)."""
    timeframe = request.args.get('timeframe', 'month')
    limit = request.args.get('limit', 20, type=int)
    
    data = ScoreService.get_leaderboard(timeframe, limit=limit)
    
    for item in data:
        item['is_current'] = (item.get('username') == current_user.username)
        
    return jsonify({
        'success': True,
        'leaderboard': data,
        'timeframe': timeframe
    })

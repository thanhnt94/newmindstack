from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import blueprint
from ..services.scoring_config_service import ScoringConfigService

@blueprint.route('/save', methods=['POST'])
@login_required
def save_scoring():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        ScoringConfigService.update_configs(settings)
        return jsonify({'success': True, 'message': 'Cập nhật hệ thống điểm số thành công.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/sync', methods=['POST'])
@login_required
def sync_scores():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        from mindstack_app.modules.gamification.interface import sync_all_users_scores
        result = sync_all_users_scores()
        return jsonify({
            'success': True, 
            'message': f"Đã đồng bộ điểm số cho {result.get('synced_count', 0)} người dùng thành công."
        })
    except Exception as e:
        current_app.logger.error(f"Error syncing scores: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

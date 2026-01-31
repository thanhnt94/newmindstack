from flask import request, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import blueprint
from ..services.reset_service import ResetService

@blueprint.route('/reset/learning', methods=['POST'])
@login_required
def reset_learning():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        ResetService.reset_learning_progress()
        return jsonify({'success': True, 'message': 'Đã xóa toàn bộ tiến độ học tập.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/reset/content', methods=['POST'])
@login_required
def reset_content():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        ResetService.reset_content()
        return jsonify({'success': True, 'message': 'Đã xóa toàn bộ nội dung.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/reset/factory', methods=['POST'])
@login_required
def factory_reset():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    # Double check confirmation logic should be in Frontend, but backend assumes confirmed if called.
    try:
        ResetService.factory_reset()
        return jsonify({'success': True, 'message': 'Factory Reset thành công.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

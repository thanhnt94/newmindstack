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

@blueprint.route('/reset/user-container', methods=['POST'])
@login_required
def reset_user_container():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    user_id = request.form.get('user_id') or request.json.get('user_id')
    container_id = request.form.get('container_id') or request.json.get('container_id')
    
    if not user_id or not container_id:
        return jsonify({'success': False, 'message': 'Thiếu user_id hoặc container_id'}), 400
    
    try:
        ResetService.reset_user_container_progress(int(user_id), int(container_id))
        return jsonify({'success': True, 'message': f'Đã xóa tiến độ của user {user_id} tại bộ học tập {container_id}.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/discovery/users', methods=['GET'])
@login_required
def discovery_users():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    try:
        users = ResetService.get_discovery_data()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/discovery/containers/<int:user_id>', methods=['GET'])
@login_required
def discovery_containers(user_id):
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    try:
        containers = ResetService.get_user_containers_discovery(user_id)
        return jsonify({'success': True, 'containers': containers})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- System Upgrade API ---

@blueprint.route('/upgrade/run', methods=['POST'])
@login_required
def run_upgrade_api():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    from ..services.system_service import SystemService
    success, message = SystemService.run_upgrade()
    return jsonify({'success': success, 'message': message})

@blueprint.route('/upgrade/status', methods=['GET'])
@login_required
def get_upgrade_status_api():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    from ..services.system_service import SystemService
    status = SystemService.get_status()
    return jsonify({'success': True, 'status': status})

@blueprint.route('/upgrade/unlock', methods=['POST'])
@login_required
def force_unlock_upgrade_api():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    from ..services.system_service import SystemService
    SystemService.force_unlock()
    return jsonify({'success': True, 'message': 'Đã mở khóa trạng thái nâng cấp.'})

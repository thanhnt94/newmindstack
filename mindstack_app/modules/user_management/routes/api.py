from flask import request, jsonify, abort
from flask_login import login_required, current_user
from .. import blueprint
from ..services.user_service import UserService
from ..schemas import UserSchema, UserProfileSchema
from mindstack_app.models import User

def admin_required():
    if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
        abort(403)

@blueprint.route('/api/status', methods=['GET'])
@login_required
def api_admin_status():
    """Basic system/user status for admin dashboard."""
    admin_required()
    pagination = UserService.get_all_users(per_page=1)
    return jsonify({
        'total_users': pagination.total,
        'admin_user': current_user.username
    })

@blueprint.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def api_get_user(user_id):
    admin_required()
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    return jsonify(UserSchema.dump(user))

@blueprint.route('/api/users/<int:user_id>/update-role', methods=['POST'])
@login_required
def api_update_user_role(user_id):
    admin_required()
    data = request.get_json()
    if not data or 'user_role' not in data:
        return jsonify({'success': False, 'message': 'Missing user_role'}), 400
    
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    user.user_role = data['user_role']
    from mindstack_app.core.extensions import db
    db.session.commit()
    
    return jsonify({'success': True})
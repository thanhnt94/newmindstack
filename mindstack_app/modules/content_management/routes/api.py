# File: mindstack_app/modules/content_management/routes/api.py
from flask import request, jsonify, abort
from flask_login import login_required, current_user
from mindstack_app.models import db, LearningContainer, LearningItem, User, ContainerContributor
from ..services.kernel_service import ContentKernelService
from mindstack_app.core.error_handlers import success_response, error_response
from sqlalchemy import func
from .. import blueprint
from ..logics.validators import has_container_access

@blueprint.route('/container/<int:container_id>/delete', methods=['POST'])
@login_required
def delete_container_api(container_id):
    if not has_container_access(container_id, 'editor'):
        abort(403)
    ContentKernelService.delete_container(container_id)
    return success_response(message="Xóa thành công", data={'container_id': container_id})

@blueprint.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item_api(item_id):
    item = LearningItem.query.get_or_404(item_id)
    if not has_container_access(item.container_id, 'editor'):
        abort(403)
    container_id = item.container_id
    ContentKernelService.delete_item(item_id)
    return success_response(message="Xóa thành công", data={'item_id': item_id, 'container_id': container_id})

@blueprint.route('/item/<int:item_id>/move', methods=['POST'])
@login_required
def move_item(item_id):
    item = LearningItem.query.get_or_404(item_id)
    if not has_container_access(item.container_id, 'editor'):
        abort(403)
    target_container_id = request.form.get('target_set_id', type=int)
    if not target_container_id or not has_container_access(target_container_id, 'editor'):
        return error_response("Không có quyền truy cập bộ đích", "FORBIDDEN", 403)
    item.container_id = target_container_id
    db.session.commit()
    return success_response(message="Di chuyển thành công")

@blueprint.route('/api/contributors/<int:container_id>/add', methods=['POST'])
@login_required
def add_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403
    data = request.get_json() or {}
    username = (data.get('username') or "").strip()
    user_to_add = User.query.filter(func.lower(User.username) == username.lower()).first()
    if not user_to_add: return {'success': False, 'message': 'User not found'}, 404
    new_c = ContainerContributor(container_id=container_id, user_id=user_to_add.user_id, permission_level=data.get('permission_level', 'editor'))
    db.session.add(new_c)
    db.session.commit()
    return {'success': True, 'message': 'Added successfully'}

@blueprint.route('/api/contributors/<int:container_id>/remove', methods=['POST'])
@login_required
def remove_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403
    data = request.get_json() or {}
    contributor = ContainerContributor.query.filter_by(container_id=container_id, user_id=data.get('user_id')).first()
    if not contributor: return {'success': False, 'message': 'Not found'}, 404
    db.session.delete(contributor)
    db.session.commit()
    return {'success': True, 'message': 'Removed successfully'}

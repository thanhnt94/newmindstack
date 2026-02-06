from flask import jsonify
from flask_login import login_required, current_user
from ..interface import AccessControlInterface
from ..schemas import UserPermissionsSchema
from ..logics.policies import get_role_policy, ROLE_FREE
from ..services.permission_service import PermissionService
from . import blueprint

@blueprint.route('/permissions/me', methods=['GET'])
@login_required
def get_my_permissions():
    """
    Get current user's permissions and quota limits.
    """
    role = PermissionService.get_role(current_user)
    policy = get_role_policy(role)
    
    # Construct response data
    data = {
        'role': role,
        'permissions': policy.get('permissions', {}),
        'quotas': {} # Logic to fetch current usage would go here if we tracked it centrally
    }
    
    # For now, just return limits as quotas structure
    limits = policy.get('limits', {})
    for key, limit in limits.items():
        data['quotas'][key] = {
            'current': 0, # Placeholder: usage tracking not yet implemented in this scope
            'limit': limit
        }

    # Serialize
    schema = UserPermissionsSchema()
    return jsonify(schema.dump(data))

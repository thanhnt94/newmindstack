from flask import current_app
from mindstack_app.core.signals import user_registered
from .services.permission_service import PermissionService
from .logics.policies import ROLE_FREE

def on_user_registered(sender, user, **kwargs):
    """
    Event listener: When a new user is registered, assign default 'free' role.
    """
    try:
        PermissionService.assign_role(user.user_id, ROLE_FREE)
        current_app.logger.info(f"Assigned default role '{ROLE_FREE}' to new user {user.username} (ID: {user.user_id})")
    except Exception as e:
        current_app.logger.error(f"Failed to assign role to user {user.user_id}: {e}")

def register_events():
    """Connect signals."""
    user_registered.connect(on_user_registered)

from typing import Union, Optional
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified

from mindstack_app.models import db, User
from ..logics.policies import get_role_policy, PolicyValues, ROLE_FREE
from ..exceptions import PermissionDeniedError, QuotaExceededError
from ..signals import role_changed, access_denied

class PermissionService:
    """Service to handle permission checks, quota enforcement, and role management."""

    @staticmethod
    def get_role(user: User) -> str:
        """Helper to get user role safely."""
        return user.user_role if user and hasattr(user, 'user_role') else ROLE_FREE

    @classmethod
    def check_permission(cls, user: User, permission_key: str) -> bool:
        """
        Check if a user has a specific permission.
        Returns check result boolean.
        """
        if not user:
            return False
        
        role = cls.get_role(user)
        policy = get_role_policy(role)
        permissions = policy.get('permissions', {})
        
        # Check explicit permission
        return permissions.get(permission_key, False)

    @classmethod
    def get_limit(cls, user: User, limit_key: str) -> Union[int, float]:
        """Get the numeric limit for a specific quota key."""
        role = cls.get_role(user)
        policy = get_role_policy(role)
        limits = policy.get('limits', {})
        return limits.get(limit_key, 0)

    @classmethod
    def check_quota(cls, user: User, limit_key: str, current_usage: int) -> bool:
        """
        Check if usage is within limits.
        Raises QuotaExceededError if limit reached.
        """
        limit = cls.get_limit(user, limit_key)
        
        if limit == PolicyValues.UNLIMITED:
            return True
            
        if current_usage >= limit:
            raise QuotaExceededError(limit_key, current_usage, int(limit))
            
        return True

    @classmethod
    def assign_role(cls, user_id: int, new_role: str) -> bool:
        """
        Assign a new role to a user.
        Updates DB and emits signal.
        """
        user = User.query.get(user_id)
        if not user:
            return False
            
        old_role = user.user_role
        if old_role == new_role:
            return True # No change
            
        user.user_role = new_role
        flag_modified(user, 'user_role')
        db.session.commit()
        
        # Emit signal
        role_changed.send(
            current_app._get_current_object(),
            user_id=user.user_id,
            old_role=old_role,
            new_role=new_role
        )
        
        current_app.logger.info(f"Role changed for user {user_id}: {old_role} -> {new_role}")
        return True

    @classmethod
    def ensure_permission(cls, user: User, permission_key: str):
        """
        Enforce permission check. Raises PermissionDeniedError if fails.
        Fires access_denied signal on failure.
        """
        if not cls.check_permission(user, permission_key):
            # Fire signal
            access_denied.send(
                current_app._get_current_object(),
                user_id=user.user_id if user else None,
                permission_key=permission_key
            )
            raise PermissionDeniedError(permission_key)

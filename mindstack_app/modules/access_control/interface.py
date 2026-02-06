from typing import Union
from .services.permission_service import PermissionService
from .exceptions import QuotaExceededError

class AccessControlInterface:
    """
    Public Gateway for Access Control Module.
    Pattern: Facade
    """

    @staticmethod
    def check(user, permission_key: str) -> bool:
        """Check if user has permission."""
        return PermissionService.check_permission(user, permission_key)

    @staticmethod
    def get_limit(user, limit_key: str) -> Union[int, float]:
        """Get resource limit for user."""
        return PermissionService.get_limit(user, limit_key)

    @staticmethod
    def enforce_quota(user, limit_key: str, current_usage: int):
        """
        Check quota and raise QuotaExceededError if violated.
        """
        PermissionService.check_quota(user, limit_key, current_usage)

    @staticmethod
    def assign_role(user_id: int, role: str) -> bool:
        """Assign role to user."""
        return PermissionService.assign_role(user_id, role)

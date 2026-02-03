from typing import Optional, Dict, Any
from .services.user_service import UserService
from .schemas import UserSchema

class UserManagementInterface:
    """Public API for the User Management module."""

    @staticmethod
    def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get basic user info as a dictionary.
        Returns primitive data types suitable for inter-module communication.
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return None
        
        # Use schema to dump data safely
        return UserSchema.dump(user)

    @staticmethod
    def check_user_exists(user_id: int) -> bool:
        """Check if a user exists."""
        return UserService.get_user_by_id(user_id) is not None

    @staticmethod
    def get_user_role(user_id: int) -> Optional[str]:
        """Get user role."""
        user = UserService.get_user_by_id(user_id)
        return user.user_role if user else None

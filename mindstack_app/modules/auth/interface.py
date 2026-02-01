# File: mindstack_app/modules/auth/interface.py
from typing import Optional
from .schemas import UserDTO, AuthResponseDTO
from .services.auth_service import AuthService
from .models import User

class AuthInterface:
    @staticmethod
    def authenticate(username_or_email: str, password: str) -> AuthResponseDTO:
        """Public API to verify user credentials."""
        user = AuthService.authenticate_user(username_or_email, password)
        if user:
            return AuthResponseDTO(
                success=True,
                user=UserDTO(
                    id=user.user_id,
                    username=user.username,
                    email=user.email,
                    role=user.user_role,
                    avatar_url=user.get_avatar_url()
                )
            )
        return AuthResponseDTO(success=False, message="Invalid credentials")

    @staticmethod
    def register(username: str, email: str, password: str) -> AuthResponseDTO:
        """Public API to register a new user."""
        try:
            user = AuthService.register_user(username, email, password)
            return AuthResponseDTO(
                success=True,
                user=UserDTO(
                    id=user.user_id,
                    username=user.username,
                    email=user.email,
                    role=user.user_role
                )
            )
        except Exception as e:
            return AuthResponseDTO(success=False, message=str(e))

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[UserDTO]:
        """Public API to fetch user data by ID."""
        user = User.query.get(user_id)
        if user:
            return UserDTO(
                id=user.user_id,
                username=user.username,
                email=user.email,
                role=user.user_role,
                avatar_url=user.get_avatar_url()
            )
        return None
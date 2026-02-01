from typing import Optional
from .schemas import UserDTO, AuthResponseDTO
from .services.auth_service import AuthService

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

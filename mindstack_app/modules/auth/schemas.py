from dataclasses import dataclass
from typing import Optional

@dataclass
class UserDTO:
    id: int
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None

@dataclass
class AuthResponseDTO:
    success: bool
    user: Optional[UserDTO] = None
    message: Optional[str] = None

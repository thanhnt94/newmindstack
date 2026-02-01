from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class NotificationDTO:
    """Represents a notification sent to a user."""
    id: Optional[int]
    user_id: int
    title: str
    message: Optional[str]
    type: str = "SYSTEM"
    link: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
    meta_data: Optional[Dict[str, Any]] = None

@dataclass
class PushPayloadDTO:
    """Payload for Web Push notification."""
    title: str
    body: str
    icon: Optional[str] = None
    url: Optional[str] = None

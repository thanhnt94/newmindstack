from typing import Optional, Dict, Any
from .schemas import NotificationDTO
from .services.notification_service import NotificationService

def send_notification(
    user_id: int, 
    title: str, 
    message: str, 
    type: str = 'SYSTEM', 
    link: Optional[str] = None, 
    meta_data: Optional[Dict[str, Any]] = None
) -> NotificationDTO:
    """
    Public API to send a notification to a user.
    Handles both in-app database storage and Web Push dispatch.
    """
    notif = NotificationService.create_notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link,
        meta_data=meta_data
    )
    
    # Convert model to DTO
    return NotificationDTO(
        id=notif.id,
        user_id=notif.user_id,
        title=notif.title,
        message=notif.message,
        type=notif.type,
        link=notif.link,
        is_read=notif.is_read,
        created_at=notif.created_at,
        meta_data=notif.meta_data
    )

def get_unread_count(user_id: int) -> int:
    """Get the number of unread notifications for a user."""
    return NotificationService.get_unread_count(user_id)

def mark_notification_read(notification_id: int, user_id: int) -> bool:
    """Mark a specific notification as read."""
    return NotificationService.mark_as_read(notification_id, user_id)

def notify_achievement_unlock(user_id: int, achievement_name: str, icon: str = 'trophy'):
    """Helper to send achievement unlock notification."""
    NotificationService.send_achievement_unlock(user_id, achievement_name, icon)

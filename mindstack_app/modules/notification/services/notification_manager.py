"""
Notification Manager Service.

Acts as the "Notification Hub" that listens to system signals, format messages using templates/logic,
and dispatches them via DeliveryService.
"""

from flask import current_app, url_for
from mindstack_app.models import db, User, PushSubscription, NotificationPreference
from mindstack_app.core.signals import (
    user_registered,
    # session_completed, # Maybe too spammy for push? Useful for "Daily Goal Met"
    # achievement_unlocked, # Needed
)
# We might need to import custom signals from other modules if they aren't in core/signals yet?
# e.g. from mindstack_app.modules.gamification.signals import level_up
# For now, let's assume we use what's available or simulated.

from mindstack_app.services.delivery_service import DeliveryService

class NotificationManager:
    """Orchestrates notification logic."""

    @staticmethod
    def init_listeners():
        """Connect signal handlers."""
        user_registered.connect(NotificationManager.on_user_registered)
        # achievement_unlocked.connect(NotificationManager.on_achievement_unlocked) 
        # Add more...

    @staticmethod
    def on_user_registered(sender, **kwargs):
        """Welcome new users."""
        user = kwargs.get('user')
        if not user:
            return
            
        try:
            # 1. Create In-App Notification
            DeliveryService.send_in_app(
                user_id=user.user_id,
                title="Chào mừng đến với MindStack!",
                message="Hãy bắt đầu hành trình học tập của bạn ngay hôm nay.",
                link="/dashboard",
                meta={'type': 'WELCOME'}
            )
            
            # 2. Check Preferences for Email (Default is often True)
            # DeliveryService.send_email(user.email, "Welcome...", "...")
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error in NotificationManager (register): {e}")

    @staticmethod
    def send_system_notification(user_id: int, title: str, message: str, link: str = None):
        """
        Public method for other modules to request a notification 
        (if they can't use signals, though signals are preferred).
        """
        # Listeners are better, but sometimes manual trigger is needed (e.g. Admin Broadcast)
        
        # Check preferences
        pref = NotificationPreference.query.get(user_id)
        if pref and not pref.system_messages:
            return # User disabled system messages
        
        DeliveryService.send_in_app(user_id, title, message, link)
        
        # If urgent, push?
        if pref and pref.push_enabled:
            pass # lookup push subscription and send

        db.session.commit()

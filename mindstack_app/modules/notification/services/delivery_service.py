"""
Delivery Service.

This service abstracts the technical details of sending messages via different channels
(Email, Web Push, In-App). It effectively acts as the "Driver" layer.
"""

from typing import Optional, Dict, Any, List
# import smtplib # for email
# from pywebpush import webpush # for push

class DeliveryService:
    """Infrastructure service for sending notifications."""

    @staticmethod
    def send_email(to_email: str, subject: str, body_html: str) -> bool:
        """
        Send an email via SMTP.
        TODO: Integrate with Flask-Mail or external provider (SendGrid, SES).
        For now, this is a stub.
        """
        try:
            # Placeholder implementation
            print(f"[DeliveryService] Mock sending email to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"[DeliveryService] Email failed: {e}")
            return False

    @staticmethod
    def send_web_push(subscription_info: Dict, payload: Dict) -> bool:
        """
        Send a Web Push notification using pywebpush.
        
        Args:
            subscription_info: Dict with endpoint, keys (auth, p256dh).
            payload: JSON payload to send.
        """
        try:
            # Placeholder implementation
            # from pywebpush import webpush, WebPushException
            # webpush(
            #     subscription_info=subscription_info,
            #     data=json.dumps(payload),
            #     vapid_private_key=...,
            #     vapid_claims=...
            # )
            print(f"[DeliveryService] Mock sending push to {subscription_info.get('endpoint')[:20]}...")
            return True
        except Exception as e:
            print(f"[DeliveryService] Push failed: {e}")
            return False

    @staticmethod
    def send_in_app(user_id: int, title: str, message: str, link: str = None, meta: Dict = None) -> Any:
        """
        Save an in-app notification to the database.
        This actually accesses the model directly, so it's a bit of a hybrid.
        Usually 'Services' call 'Repositories/Kernels' for DB access.
        """
        from mindstack_app.core.extensions import db
        from ..models import Notification
        
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            link=link,
            meta_data=meta,
            is_read=False,
            type='SYSTEM' # Default, caller can override if we add arg
        )
        db.session.add(notif)
        # Commit should ideally be handled by the caller (Unit of Work), 
        # but for simplicity in this service method we might flush it or let caller commit.
        # Let's flush so meaningful ID generates.
        db.session.flush()
        return notif

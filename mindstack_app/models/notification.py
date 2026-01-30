from datetime import datetime, timezone
from mindstack_app.core.extensions import db
from sqlalchemy.sql import func

class Notification(db.Model):
    """Stores user notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Types: SYSTEM, STUDY, CHAT, ACHIEVEMENT
    type = db.Column(db.String(50), default='SYSTEM') 
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(500), nullable=True)
    
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Stores JSON data like {'room_id': '123'} or {'sender_avatar': '...'}
    meta_data = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'meta_data': self.meta_data
        }

class PushSubscription(db.Model):
    """Stores Web Push API subscriptions."""
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    auth_key = db.Column(db.String(200), nullable=False)
    p256dh_key = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'endpoint': self.endpoint,
            'keys': {
                'auth': self.auth_key,
                'p256dh': self.p256dh_key
            }
        }

class NotificationPreference(db.Model):
    """Stores user's notification preferences."""
    __tablename__ = 'notification_preferences'

    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    
    email_enabled = db.Column(db.Boolean, default=True)
    push_enabled = db.Column(db.Boolean, default=True)
    
    # Specific categories
    study_reminders = db.Column(db.Boolean, default=True)
    achievement_updates = db.Column(db.Boolean, default=True)
    system_messages = db.Column(db.Boolean, default=True)
    marketing_updates = db.Column(db.Boolean, default=False)
    
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

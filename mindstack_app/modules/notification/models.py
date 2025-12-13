from datetime import datetime
from ...db_instance import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Types: SYSTEM, STUDY, CHAT, ACHIEVEMENT
    type = db.Column(db.String(50), default='SYSTEM') 
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(500), nullable=True)
    
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    auth_key = db.Column(db.String(200), nullable=False)
    p256dh_key = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'endpoint': self.endpoint,
            'keys': {
                'auth': self.auth_key,
                'p256dh': self.p256dh_key
            }
        }

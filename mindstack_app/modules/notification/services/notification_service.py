from flask import current_app
import json
try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None

from mindstack_app.core.extensions import db
from ..models import Notification, PushSubscription

class NotificationService:
    @staticmethod
    def create_notification(user_id, title, message, type='SYSTEM', link=None, meta_data=None):
        """Creates a new notification and potentially triggers Push."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            link=link,
            meta_data=meta_data
        )
        db.session.add(notif)
        db.session.commit()
        
        # Trigger Web Push
        NotificationService.send_web_push(user_id, {
            'title': title,
            'body': message,
            'icon': '/static/icons/icon-192x192.png', # Placeholder
            'data': {'url': link}
        })
        
        return notif

    @staticmethod
    def send_web_push(user_id, payload_data):
        if not webpush:
            return

        subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
        if not subscriptions:
            return

        vapid_private = current_app.config.get('VAPID_PRIVATE_KEY')
        vapid_email = current_app.config.get('VAPID_EMAIL')
        
        if not vapid_private:
            return

        json_payload = json.dumps(payload_data)

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {
                            "auth": sub.auth_key,
                            "p256dh": sub.p256dh_key
                        }
                    },
                    data=json_payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_email}
                )
            except WebPushException as ex:
                if ex.response and ex.response.status_code == 410:
                    db.session.delete(sub)
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Push Error: {e}")

    @staticmethod
    def get_unread_count(user_id):
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def get_user_notifications(user_id, limit=20, offset=0):
        return Notification.query.filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc())\
            .limit(limit).offset(offset).all()

    @staticmethod
    def mark_as_read(notification_id, user_id):
        notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notif:
            notif.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id):
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return True

    @staticmethod
    def delete(notification_id, user_id):
        notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notif:
            db.session.delete(notif)
            db.session.commit()
            return True
        return False
        
    @staticmethod
    def check_daily_study_reminder(user_id):
        from sqlalchemy import func
        from datetime import datetime, date, timedelta
        from mindstack_app.models import ScoreLog
        
        # 1. Check if user studied today (any ScoreLog)
        today = date.today()
        has_studied = ScoreLog.query.filter(
            ScoreLog.user_id == user_id,
            func.date(ScoreLog.timestamp) == today
        ).first() is not None
        
        if has_studied:
            return False # User already studied

        # 2. Check if we already sent a reminder today
        # We look for a notification of type 'STUDY' created today
        already_notified = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.type == 'STUDY',
            func.date(Notification.created_at) == today
        ).first() is not None
        
        if already_notified:
            return False
            
        # 3. Send Reminder
        NotificationService.create_notification(
            user_id=user_id,
            title="Đừng quên học bài hôm nay!",
            message="Bạn chưa luyện tập hôm nay. Hãy dành 5 phút để duy trì chuỗi nhé!",
            type='STUDY',
            link='/quiz/dashboard'
        )
        return True

    @staticmethod
    def send_achievement_unlock(user_id, achievement_name, achievement_icon='trophy'):
        """Send a notification when an achievement is unlocked."""
        NotificationService.create_notification(
            user_id=user_id,
            title=f"Thành tích mới: {achievement_name}!",
            message="Chúc mừng! Bạn đã mở khóa một thành tích mới trên hành trình học tập.",
            type='ACHIEVEMENT',
            link='/profile/achievements'
        )

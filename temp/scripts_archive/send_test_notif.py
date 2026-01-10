import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from mindstack_app import create_app, db
from mindstack_app.modules.notification.services import NotificationService
from mindstack_app.models import User

app = create_app()

with app.app_context():
    # Get first admin or user
    user = User.query.first()
    if user:
        print(f"Sending test notification to User ID: {user.user_id} ({user.username})")
        NotificationService.create_notification(
            user_id=user.user_id,
            title="Chào mừng đến với MindStack!",
            message="Đây là thông báo thử nghiệm đầu tiên của bạn. Hệ thống thông báo đã hoạt động!",
            type="SYSTEM",
            link="/profile/view"
        )
        print("Notification sent successfully!")
    else:
        print("No users found in database.")

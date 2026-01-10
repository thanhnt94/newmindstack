import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from mindstack_app import create_app, db
from mindstack_app.modules.notification.services import NotificationService
from mindstack_app.models import User

app = create_app()

with app.app_context():
    print("Running Daily Study Check...")
    users = User.query.all()
    count = 0
    for user in users:
        # Skip admins if desired, but good for testing
        print(f"Checking user {user.username}...")
        if NotificationService.check_daily_study_reminder(user.user_id):
            print(f" -> Sent reminder to {user.username}")
            count += 1
        else:
            print(" -> No reminder needed.")
            
    print(f"Done. Sent {count} reminders.")

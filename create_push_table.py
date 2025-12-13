import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from mindstack_app import create_app, db
from mindstack_app.modules.notification.models import PushSubscription

app = create_app()

with app.app_context():
    print("Creating push_subscriptions table...")
    try:
        db.create_all()
        print("Tables created successfully!")
        
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'push_subscriptions' in tables:
            print("✅ Table 'push_subscriptions' exists.")
        else:
            print("❌ Table 'push_subscriptions' was NOT created.")
            
    except Exception as e:
        print(f"Error creating tables: {e}")

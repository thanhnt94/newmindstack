import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from mindstack_app import create_app, db
from mindstack_app.modules.notification.models import Notification  # Register Model

app = create_app()

with app.app_context():
    print("Creating database tables...")
    try:
        db.create_all()
        print("Tables created successfully!")
        
        # Verify table existence
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'notifications' in tables:
            print("✅ Table 'notifications' exists.")
        else:
            print("❌ Table 'notifications' was NOT created.")
            
    except Exception as e:
        print(f"Error creating tables: {e}")

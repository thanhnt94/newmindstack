import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app
from mindstack_app.core.extensions import db

# Explicitly import models to ensure they are registered with SQLAlchemy
# (Although create_app -> bootstrap_system -> register_all_models should handle this,
# explicit imports here guarantee visibility for this script context if bootstrap varies)
from mindstack_app.modules.goals.models import Goal, UserGoal, GoalProgress
from mindstack_app.modules.learning_history.models import StudyLog

def init_tables():
    app = create_app()
    with app.app_context():
        print("Initializing database tables...")
        # create_all() creates only tables that don't exist
        db.create_all()
        print("Database tables initialized successfully.")
        
        # Verify user_goals specifically
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        if 'user_goals' in tables:
            print("[OK] Table 'user_goals' exists.")
        else:
            print("[ERROR] Table 'user_goals' was NOT created.")

        if 'study_logs' in tables:
            print("[OK] Table 'study_logs' exists.")
        else:
            print("[ERROR] Table 'study_logs' was NOT created.")

if __name__ == '__main__':
    init_tables()

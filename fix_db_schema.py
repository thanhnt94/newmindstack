from mindstack_app import create_app
from mindstack_app.extensions import db
from mindstack_app.models.learning_session import LearningSession
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Dropping legacy learning_sessions table...")
    try:
        db.session.execute(text("DROP TABLE learning_sessions"))
        db.session.commit()
        print("Dropped successfully.")
    except Exception as e:
        print(f"Error dropping table: {e}")
        db.session.rollback()

    print("Recreating tables...")
    db.create_all()
    print("Done. Please check the schema now.")

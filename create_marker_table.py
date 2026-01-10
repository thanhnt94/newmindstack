from mindstack_app import create_app, db
from mindstack_app.models import UserItemMarker
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    if 'user_item_markers' not in inspector.get_table_names():
        print("Creating user_item_markers table...")
        # Create specifically this table
        UserItemMarker.__table__.create(db.engine)
        print("Table created successfully.")
    else:
        print("Table user_item_markers already exists.")

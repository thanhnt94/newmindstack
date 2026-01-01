"""Add custom_data column to learning_items table."""
from mindstack_app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE learning_items ADD COLUMN custom_data TEXT'))
            conn.commit()
            print('✓ Added custom_data column to learning_items!')
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print('Column already exists, skipping.')
            else:
                raise

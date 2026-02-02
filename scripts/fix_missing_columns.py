from mindstack_app.app import create_app
from mindstack_app.core.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Check existing columns
    columns_info = db.session.execute(text("PRAGMA table_info(item_memory_states)")).fetchall()
    existing_columns = [col[1] for row in columns_info for col in [row]]
    print(f"Existing columns in 'item_memory_states': {existing_columns}")
    
    # List of columns that SHOULD be there based on the model
    expected_columns = [
        ('stability', 'FLOAT'),
        ('difficulty', 'FLOAT'),
        ('state', 'INTEGER'),
        ('due_date', 'DATETIME'),
        ('last_review', 'DATETIME'),
        ('repetitions', 'INTEGER'),
        ('lapses', 'INTEGER'),
        ('streak', 'INTEGER'),
        ('incorrect_streak', 'INTEGER'),
        ('times_correct', 'INTEGER'),
        ('times_incorrect', 'INTEGER'),
        ('data', 'JSON'),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME')
    ]
    
    for col_name, col_type in expected_columns:
        if col_name not in existing_columns:
            print(f"Adding missing column: {col_name} ({col_type})")
            try:
                # SQLite ALTER TABLE only supports one column at a time
                db.session.execute(text(f"ALTER TABLE item_memory_states ADD COLUMN {col_name} {col_type}"))
                db.session.commit()
                print(f"Successfully added {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                db.session.rollback()

    # Double check study_logs as well
    columns_info = db.session.execute(text("PRAGMA table_info(study_logs)")).fetchall()
    existing_columns = [col[1] for row in columns_info for col in [row]]
    print(f"Existing columns in 'study_logs': {existing_columns}")
    
    expected_logs = [
        ('rating', 'INTEGER'),
        ('user_answer', 'TEXT'),
        ('is_correct', 'BOOLEAN'),
        ('review_duration', 'INTEGER'),
        ('session_id', 'INTEGER'),
        ('container_id', 'INTEGER'),
        ('learning_mode', 'VARCHAR(50)'),
        ('fsrs_snapshot', 'JSON'),
        ('gamification_snapshot', 'JSON')
    ]
    
    for col_name, col_type in expected_logs:
        if col_name not in existing_columns:
            print(f"Adding missing column to study_logs: {col_name}")
            try:
                db.session.execute(text(f"ALTER TABLE study_logs ADD COLUMN {col_name} {col_type}"))
                db.session.commit()
            except Exception as e:
                print(f"Error: {e}")
                db.session.rollback()

    print("Migration check complete.")

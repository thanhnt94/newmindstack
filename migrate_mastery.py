"""Database migration script: Add mastery column to progress tables."""

from mindstack_app import create_app
from mindstack_app.db_instance import db
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        # Check if mastery column exists in flashcard_progress
        result = db.session.execute(text("PRAGMA table_info(flashcard_progress)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'mastery' not in columns:
            print('Adding mastery column to flashcard_progress...')
            db.session.execute(text('ALTER TABLE flashcard_progress ADD COLUMN mastery REAL DEFAULT 0.0'))
            db.session.commit()
            print('Done!')
        else:
            print('mastery column already exists in flashcard_progress')
        
        # Check quiz_progress
        result2 = db.session.execute(text("PRAGMA table_info(quiz_progress)")).fetchall()
        columns2 = [row[1] for row in result2]
        
        if 'mastery' not in columns2:
            print('Adding mastery column to quiz_progress...')
            db.session.execute(text('ALTER TABLE quiz_progress ADD COLUMN mastery REAL DEFAULT 0.0'))
            db.session.commit()
            print('Done!')
        else:
            print('mastery column already exists in quiz_progress')
        
        # Populate existing records with calculated mastery
        print('Populating mastery for existing records...')
        
        # Simple estimation: based on status and repetitions
        db.session.execute(text('''
            UPDATE flashcard_progress SET mastery = 
                CASE 
                    WHEN status = 'new' THEN 0.0
                    WHEN status = 'learning' THEN 0.1 + MIN(repetitions, 7) * 0.06
                    WHEN status = 'reviewing' THEN 0.6 + MIN(repetitions, 7) * 0.057
                    ELSE 0.0
                END
            WHERE mastery IS NULL OR mastery = 0.0
        '''))
        
        db.session.execute(text('''
            UPDATE quiz_progress SET mastery = 
                CASE 
                    WHEN status = 'new' THEN 0.0
                    WHEN status = 'learning' THEN 0.1 + MIN(times_correct, 7) * 0.06
                    WHEN status = 'reviewing' THEN 0.6 + MIN(times_correct, 7) * 0.057
                    ELSE 0.0
                END
            WHERE mastery IS NULL OR mastery = 0.0
        '''))
        
        db.session.commit()
        print('Migration complete!')


if __name__ == '__main__':
    run_migration()

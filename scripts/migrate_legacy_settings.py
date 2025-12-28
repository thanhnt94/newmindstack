import sys
import os

# Add project root to path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app, db
from mindstack_app.models import LearningContainer

def migrate_settings():
    """
    Migrates data from 'legacy_ai_settings' JSON column to new structured columns
    (ai_prompt, ai_capabilities, media_image_folder, media_audio_folder).
    """
    print("Initializing application context...")
    app = create_app()
    with app.app_context():
        print("Checking for containers needing migration...")
        containers = LearningContainer.query.all()
        migrated_count = 0
        
        for container in containers:
            # Check if there is legacy data
            legacy_data = container.legacy_ai_settings
            
            # Even if legacy_ai_settings is None, we might want to normalize existing data,
            # but primarily we care about legacy data migration.
            if legacy_data:
                print(f"Migrating Container ID {container.container_id}: {container.title}")
                
                # Reading .ai_settings property merges new columns + legacy data
                current_settings = container.ai_settings
                
                # Writing back to .ai_settings property triggers the setter logic
                # which distributes values to the new columns (ai_prompt, etc.)
                # and updates legacy_ai_settings with any remaining 'extra' data.
                container.ai_settings = current_settings
                
                migrated_count += 1
        
        if migrated_count > 0:
            print(f"Committing changes for {migrated_count} containers...")
            db.session.commit()
            print("Migration successful.")
        else:
            print("No containers needed migration (or no legacy data found).")

if __name__ == "__main__":
    migrate_settings()

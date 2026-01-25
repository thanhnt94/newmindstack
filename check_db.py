from mindstack_app import app, db
from mindstack_app.models import LearningContainer, User

with app.app_context():
    print(f"DATABASE URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    import os
    print(f"CWD: {os.getcwd()}")
    
    print("--- ALL CONTAINERS ---")
    all_c = LearningContainer.query.limit(10).all()
    for c in all_c:
        print(f"ID: {c.container_id}, Type: {c.container_type}, Title: {c.title}")

    print("--- LATEST FLASHCARD SETS ---")
    sets = LearningContainer.query.filter_by(container_type='FLASHCARD_SET').order_by(LearningContainer.created_at.desc()).limit(5).all()
    for s in sets:
        print(f"ID: {s.container_id}, Title: {s.title}, Creator: {s.creator_user_id}, Created At: {s.created_at}, Is Public: {s.is_public}")
    
    print("\n--- CURRENT USER INFO (FOR DEBUG) ---")
    # This won't work perfectly in a script without session, but we can check the admin user
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"Admin User ID: {admin.user_id}, Role: {admin.user_role}")
    
    total = LearningContainer.query.filter_by(container_type='FLASHCARD_SET').count()
    print(f"\nTotal Flashcard Sets: {total}")

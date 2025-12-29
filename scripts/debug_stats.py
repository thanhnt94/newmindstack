from mindstack_app import create_app, db
from mindstack_app.modules.learning.services.srs_service import SrsService
import sys
import traceback

app = create_app()

with app.app_context():
    print("Testing SrsService.get_container_stats...")
    try:
        # Use user 1 (admin) and a container ID. 
        # Need to find a valid container. 
        from mindstack_app.models import LearningContainer, User
        admin = User.query.first()
        if not admin:
            print("No users found")
            sys.exit(1)
        
        container = LearningContainer.query.first()
        if not container:
             print("No containers found")
             sys.exit(0)
             
        print(f"User: {admin.username} ({admin.user_id})")
        print(f"Container: {container.title} ({container.container_id})")

        stats = SrsService.get_container_stats(admin.user_id, container.container_id, 'flashcard')
        print("Success:", stats)
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()

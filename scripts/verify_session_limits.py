
import os
import sys

# Add the project root to the python path
project_root = r"c:\Code\MindStack\newmindstack"
sys.path.append(project_root)

from mindstack_app import create_app
from mindstack_app.models import User, LearningItem, LearningContainer, db
from mindstack_app.modules.vocabulary.driver import VocabularyDriver
from mindstack_app.modules.learning.services.settings_service import LearningSettingsService

def verify_new_limit():
    app = create_app()
    with app.app_context():
        # 1. Find a user and a container with many items
        user = User.query.first()
        if not user:
            print("No user found.")
            return

        container = LearningContainer.query.filter(LearningContainer.container_type == 'FLASHCARD_SET').first()
        if not container:
            print("No flashcard set found.")
            return

        print(f"Testing for User: {user.username} (ID: {user.user_id})")
        print(f"Testing for Container: {container.title} (ID: {container.container_id})")

        # 2. Test default limit (should be 999,999 now)
        driver = VocabularyDriver()
        settings = {'filter': 'srs', 'mode': 'flashcard'}
        state = driver.initialize_session(container.container_id, user.user_id, settings)
        
        print(f"Default session size: {state.total_items}")
        
        # 3. Test explicit limit via URL-like params
        url_params = {'new_limit': '5'}
        resolved_config = LearningSettingsService.resolve_flashcard_session_config(user, container.container_id, url_params)
        print(f"Resolved config with new_limit=5: {resolved_config}")
        
        settings['new_limit'] = resolved_config['new_limit']
        state_limited = driver.initialize_session(container.container_id, user.user_id, settings)
        print(f"Limited session size (expected around 5 + due): {state_limited.total_items}")

if __name__ == "__main__":
    verify_new_limit()

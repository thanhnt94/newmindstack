"""
Debug: Simulate API call to check what user_button_count is returned
"""
import sys
sys.path.insert(0, '.')

from mindstack_app import create_app
from mindstack_app.models import db, UserContainerState, User

app = create_app()

with app.app_context():
    # Simulate what api_get_flashcard_modes does
    set_id = 7
    user_id = 1  # Assuming this is the logged in user
    
    user_button_count = 4  # Default
    uc_state = None
    
    uc_state = UserContainerState.query.filter_by(
        user_id=user_id, 
        container_id=set_id
    ).first()
    
    print(f"UserContainerState found: {uc_state is not None}")
    
    if uc_state:
        print(f"Settings: {uc_state.settings}")
        
        if uc_state.settings:
            flashcard_settings = uc_state.settings.get('flashcard', {})
            print(f"Flashcard settings: {flashcard_settings}")
            
            if 'button_count' in flashcard_settings:
                user_button_count = flashcard_settings['button_count']
                print(f"button_count found in settings: {user_button_count}")
            else:
                print("button_count NOT found in flashcard_settings")
        else:
            print("Settings is None or empty")
    else:
        print("No UserContainerState found")
    
    print(f"\nFinal user_button_count that would be returned: {user_button_count}")
    
    # Also check what the API response would look like
    response = {
        'success': True,
        'user_button_count': user_button_count,
        'settings': uc_state.settings if (uc_state and uc_state.settings) else {}
    }
    print(f"\nAPI Response preview: {response}")

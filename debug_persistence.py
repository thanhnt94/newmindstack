
from mindstack_app import create_app, db
from mindstack_app.models import UserContainerState, User

app = create_app()

def debug_user_settings(username=None):
    with app.app_context():
        if username:
            user = User.query.filter_by(username=username).first()
        else:
            user = User.query.first() # Default to first user if not specified
            
        if not user:
            print("No user found!")
            return

        print(f"--- Debugging Settings for User: {user.username} (ID: {user.user_id}) ---")
        
        states = UserContainerState.query.filter_by(user_id=user.user_id).all()
        
        if not states:
            print("No saved settings found for any set.")
            return

        for state in states:
            if state.settings:
                print(f"\n[Set ID: {state.container_id}]")
                print(f"  Settings JSON: {state.settings}")
                if 'flashcard' in state.settings:
                    fc = state.settings['flashcard']
                    print(f"  -> Flashcard Button Count: {fc.get('button_count', 'Not Set')}")
            else:
                # print(f"Set ID: {state.container_id} - No settings")
                pass
        
        print("\n--- End Debug ---")

if __name__ == "__main__":
    # You can change the username here if needed
    debug_user_settings()

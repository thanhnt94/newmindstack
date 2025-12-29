
from mindstack_app import create_app, db
from mindstack_app.models import User, UserContainerState
from flask_login import login_user

app = create_app()

def verify_api_settings():
    with app.test_client() as client:
        with app.app_context():
            # Setup User
            user = User.query.first()
            if not user:
                print("No user found.")
                return

            print(f"Testing with User: {user.username} (ID: {user.user_id})")
            
            # Login Helper
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.user_id)
                sess['_fresh'] = True

            set_id = 7 # Using the set ID from previous context

            # Test 1: POST Settings (Auto Save = False)
            print("\n[Test 1] POST /api/settings/container/7 (auto_save=False)")
            resp = client.post(f'/learn/vocabulary/api/settings/container/{set_id}', 
                               json={'auto_save': False, 'custom_key': 'test'})
            
            if resp.status_code == 200:
                print(" -> Success: API returned 200")
                data = resp.get_json()
                print(f" -> Response Data: {data}")
                
                # Check DB
                uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
                if uc_state and uc_state.settings.get('auto_save') is False:
                     print(" -> VERIFIED: DB updated correctly (auto_save=False)")
                else:
                     print(f" -> FAILED: DB Value is {uc_state.settings}")
            else:
                print(f" -> Failed: {resp.status_code} - {resp.data}")

            # Test 2: GET Modes (Should include settings)
            print("\n[Test 2] GET /learn/vocabulary/api/flashcard-modes/7")
            resp = client.get(f'/learn/vocabulary/api/flashcard-modes/{set_id}')
            if resp.status_code == 200:
                data = resp.get_json()
                print(f"DEBUG DATA: {data}") # ADDED
                if 'settings' in data and data['settings'].get('auto_save') is False:
                    print(" -> VERIFIED: API returns settings correctly.")
                else:
                    print(f" -> FAILED: Settings missing or incorrect in response. Settings: {data.get('settings')}")
            else:
                print(f" -> Failed: {resp.status_code}")

            # Test 3: DELETE Settings (Reset)
            print("\n[Test 3] DELETE /learn/vocabulary/api/settings/container/7")
            resp = client.delete(f'/learn/vocabulary/api/settings/container/{set_id}')
            if resp.status_code == 200:
                 # Check DB
                uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
                if uc_state and not uc_state.settings:
                     print(" -> VERIFIED: DB settings cleared.")
                else:
                     print(f" -> FAILED: DB Settings still exist: {uc_state.settings}")

            print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_api_settings()


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

            set_id = 7 

            # Test 1: POST Settings (Auto Save = False)
            print("\n[Test 1] POST /api/settings/container/7 (auto_save=False)")
            resp = client.post(f'/learn/vocabulary/api/settings/container/{set_id}', 
                               json={'auto_save': False, 'custom_key': 'test'})
            
            if resp.status_code == 200:
                print(" -> POST Success")
                
                # Force reload from DB
                db.session.expire_all()
                
                # Check DB
                uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
                if uc_state:
                     print(f" -> DB Settings: {uc_state.settings}")
                     if uc_state.settings.get('auto_save') is False:
                         print(" -> VERIFIED: DB updated correctly (auto_save=False)")
                     else:
                         print(f" -> FAILED: auto_save != False")
                else:
                     print(" -> FAILED: No record found")
            else:
                print(f" -> Failed: {resp.status_code} - {resp.data}")

            # Test 2: GET Modes (Should include settings)
            print("\n[Test 2] GET /learn/vocabulary/api/flashcard-modes/7")
            resp = client.get(f'/learn/vocabulary/api/flashcard-modes/{set_id}')
            if resp.status_code == 200:
                data = resp.get_json()
                print(f" -> API Response Settings: {data.get('settings')}")
                # print(f"DEBUG DATA: {data}")
                if 'settings' in data and data['settings'].get('auto_save') is False:
                    print(" -> VERIFIED: API returns settings correctly.")
                else:
                    print(f" -> FAILED: Settings missing or incorrect in response.")
            else:
                print(f" -> Failed: {resp.status_code}")

            # Test 3: DELETE Settings (Reset)
            print("\n[Test 3] DELETE /learn/vocabulary/api/settings/container/7")
            resp = client.delete(f'/learn/vocabulary/api/settings/container/{set_id}')
            if resp.status_code == 200:
                db.session.expire_all()
                # Check DB
                uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
                # Settings should be empty dict or at least auto_save gone
                if uc_state: 
                    print(f" -> DB Settings After Reset: {uc_state.settings}")
                    if not uc_state.settings or 'auto_save' not in uc_state.settings:
                        print(" -> VERIFIED: reset successful.")
                else:
                    print(" -> VERIFIED: Record gone or reset successful.")

            print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_api_settings()

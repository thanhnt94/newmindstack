
from mindstack_app import create_app, db
from mindstack_app.models import User, UserContainerState
from flask import session

app = create_app()

def verify_dashboard_logic():
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

            # --- SETUP: Reset to Clean Slate ---
            print("\n[Setup] Resetting settings...")
            client.delete(f'/learn/vocabulary/api/settings/container/{set_id}')
            db.session.expire_all()

            # --- TEST 1: Auto Mode (Default) ---
            print("\n[Test 1] Auto Mode Logic")
            # Default is auto_save=True (implicitly or explicitly)
            
            # Simulate Starting Session with 6 buttons
            print(" -> Starting session with 6 buttons (Auto)...")
            client.get(f'/learn/vocabulary/flashcard/start/{set_id}/new?rating_levels=6')
            
            db.session.expire_all()
            uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
            val = uc_state.settings['flashcard']['button_count']
            if val == 6:
                print(" -> PASS: DB updated to 6.")
            else:
                print(f" -> FAIL: DB is {val}, expected 6.")

            # Simulate Starting Session with 4 buttons
            print(" -> Starting session with 4 buttons (Auto override)...")
            client.get(f'/learn/vocabulary/flashcard/start/{set_id}/new?rating_levels=4')
            
            db.session.expire_all()
            uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
            val = uc_state.settings['flashcard']['button_count']
            if val == 4:
                print(" -> PASS: DB updated to 4.")
            else:
                print(f" -> FAIL: DB is {val}, expected 4.")


            # --- TEST 2: Fixed Mode ---
            print("\n[Test 2] Fixed Mode Logic")
            
            # User sets Fixed Mode = 3 buttons (via Modal)
            print(" -> Saving Settings: Fixed Mode, 3 buttons...")
            client.post(f'/learn/vocabulary/api/settings/container/{set_id}', 
                        json={'auto_save': False, 'flashcard': {'button_count': 3}})
            
            db.session.expire_all()
            uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
            if uc_state.settings.get('auto_save') is False and uc_state.settings['flashcard']['button_count'] == 3:
                 print(" -> PASS: DB Settings saved correctly (Fixed=3).")
            else:
                 print(f" -> FAIL: DB Settings incorrect: {uc_state.settings}")

            # Simulate Starting Session with 6 buttons (Override)
            print(" -> Starting session with 6 buttons (Fixed override)...")
            client.get(f'/learn/vocabulary/flashcard/start/{set_id}/new?rating_levels=6')
            
            db.session.expire_all()
            # DB should STILL be 3
            uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=set_id).first()
            val = uc_state.settings['flashcard']['button_count']
            if val == 3:
                print(" -> PASS: DB Remained 3 (Correctly ignored update).")
            else:
                print(f" -> FAIL: DB updated to {val} (Should have stayed 3).")

            print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_dashboard_logic()

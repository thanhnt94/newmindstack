import sys
import os
sys.path.append(os.getcwd())
from mindstack_app import create_app, db
from mindstack_app.models import User

app = create_app('development')

with app.app_context():
    # Identify a user to test with, e.g., the first available user or admin
    user = User.query.first()
    if not user:
        print("No user found to test session page.")
        exit(1)

    print(f"Testing with user: {user.username} (ID: {user.user_id})")

    # Use test client
    with app.test_client() as client:
        # Login (simulate session)
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.user_id)
            sess['_fresh'] = True
        
        # Access /session/
        try:
            response = client.get('/session/', follow_redirects=True)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("Page loaded successfully.")
                if b'Quan ly phien hoc' in response.data or b'Sessions' in response.data or b'phien hoc' in response.data.lower():
                     print("Content check passed (found session keywords).")
                else:
                     print("WARNING: Content might be empty or unexpected.")
                     print("Response snippet:", response.data[:500])
            else:
                print("Error loading page.")
                print("Response snippet:", response.data[:500])
                
        except Exception as e:
            print(f"Exception during request: {e}")


import sys
import traceback
from mindstack_app import create_app
from flask import url_for

try:
    print("Creating app...")
    app = create_app()
    with app.app_context():
        print("Successfully created app context.")
        with app.test_request_context():
            try:
                url = url_for('learning.practice_hub')
                print(f"SUCCESS: Endpoint 'learning.practice_hub' maps to: {url}")
            except Exception as e:
                print(f"FAIL: Error resolving 'learning.practice_hub': {e}")
                
            try:
                url2 = url_for('learning.flashcard_dashboard')
                print(f"SUCCESS: Endpoint 'learning.flashcard_dashboard' maps to: {url2}")
            except Exception as e:
                print(f"FAIL: Error resolving 'learning.flashcard_dashboard': {e}")
                
            try:
                url3 = url_for('vocab_flashcard.flashcard_learning.api_get_flashcard_item_details', item_id=1)
                print(f"SUCCESS: Endpoint 'vocab_flashcard.flashcard_learning.api_get_flashcard_item_details' maps to: {url3}")
            except Exception as e:
                print(f"FAIL: Error resolving 'vocab_flashcard.flashcard_learning.api_get_flashcard_item_details': {e}")

            # print("Checking URL Map for 'learning':")
            # for rule in app.url_map.iter_rules():
            #     if 'learning' in rule.endpoint:
            #         print(f" - {rule.endpoint}: {rule}")

except Exception as e:
    print("CRITICAL: Failed to create app.")
    traceback.print_exc()

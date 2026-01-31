"""
Quick test script to verify autogen API endpoints
Run this from the project root: python -m mindstack_app.modules.AI.tests.test_autogen
"""

from mindstack_app import create_app
from mindstack_app.models import db
from mindstack_app.modules.AI.services.autogen_service import get_sets_with_missing_content

def test_get_sets():
    app = create_app()
    with app.app_context():
        print("\n=== Testing Quiz Sets ===")
        quiz_result = get_sets_with_missing_content('quiz')
        print(f"Success: {quiz_result.get('success')}")
        if quiz_result.get('success'):
            print(f"Found {len(quiz_result.get('sets', []))} quiz sets:")
            for s in quiz_result.get('sets', []):
                print(f"  - {s['name']}: {s['missing']}/{s['total']} missing")
        else:
            print(f"Error: {quiz_result.get('message')}")
        
        print("\n=== Testing Flashcard Sets ===")
        flashcard_result = get_sets_with_missing_content('flashcard')
        print(f"Success: {flashcard_result.get('success')}")
        if flashcard_result.get('success'):
            print(f"Found {len(flashcard_result.get('sets', []))} flashcard sets:")
            for s in flashcard_result.get('sets', []):
                print(f"  - {s['name']}: {s['missing']}/{s['total']} missing")
        else:
            print(f"Error: {flashcard_result.get('message')}")

if __name__ == '__main__':
    test_get_sets()

import sys
import io
from mindstack_app.models import LearningItem, db
from mindstack_app import create_app

# Force utf-8 for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = create_app()
with app.app_context():
    items = LearningItem.query.filter(LearningItem.content.isnot(None)).limit(5).all()
    
    print("--- DEBUGGING ITEM CONTENT ---")
    for item in items:
        print(f"Item ID: {item.item_id}")
        content = item.content or {}
        print(f"Keys in content: {list(content.keys())}")
        if 'custom_data' in content:
            print(f"custom_data found: {content['custom_data']}")
        else:
            print("No 'custom_data' key found.")
            # Print entire content keys to see if we missed something
            # checking common patterns like 'metadata', 'extra', etc.
            print(f"Full content sample: {str(content)[:200]}")
        
        # Also check AI explanation
        print(f"AI Explanation: {item.ai_explanation[:50] if item.ai_explanation else 'None'}")
        print("-" * 20)

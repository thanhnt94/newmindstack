from mindstack_app.models import LearningItem, db
from mindstack_app import create_app

app = create_app()
with app.app_context():
    # Fetch a few items that are likely to have custom data (e.g. from a user set)
    # Assuming user_id=1 for simplicity or just general items
    items = LearningItem.query.filter(LearningItem.content.isnot(None)).limit(5).all()
    
    print("--- DEBUGGING ITEM CONTENT ---")
    for item in items:
        print(f"Item ID: {item.item_id}")
        print(f"Keys in content: {list(item.content.keys())}")
        if 'custom_data' in item.content:
            print(f"custom_data: {item.content['custom_data']}")
        else:
            print("No 'custom_data' key found.")
            # Check if there are other keys that might be custom data
            print(f"Full content sample: {str(item.content)[:200]}")
        print("-" * 20)

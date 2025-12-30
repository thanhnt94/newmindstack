"""
Debug: Check current template settings in database
"""
import sys
sys.path.insert(0, '.')

from mindstack_app import create_app
from mindstack_app.models import AppSettings

app = create_app()

with app.app_context():
    # Check flashcard.cardsession template version
    template_type = 'flashcard.cardsession'
    key = f'template.{template_type}'
    setting = AppSettings.query.get(key)
    
    print(f"Key: {key}")
    if setting:
        print(f"Value: {setting.value}")
        print(f"Category: {setting.category}")
        print(f"Updated at: {setting.updated_at}")
    else:
        print("Not found in database - will use default")
    
    # List all template settings
    print("\n=== All template settings ===")
    template_settings = AppSettings.get_by_category('template')
    for s in template_settings:
        print(f"{s.key} = {s.value}")

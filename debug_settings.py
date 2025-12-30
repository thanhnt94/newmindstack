"""
Debug script to check UserContainerState settings in database
"""
import sys
sys.path.insert(0, '.')

from mindstack_app import create_app
from mindstack_app.models import db, UserContainerState, User

app = create_app()

with app.app_context():
    output = []
    
    output.append("=" * 60)
    output.append("DEBUG: Checking UserContainerState settings")
    output.append("=" * 60)
    
    # Get current user's container state for container 7
    state = UserContainerState.query.filter_by(container_id=7).first()
    
    if state:
        output.append(f"\nContainer ID: {state.container_id}")
        output.append(f"User ID: {state.user_id}")
        output.append(f"Settings: {state.settings}")
        output.append(f"Settings type: {type(state.settings)}")
        
        if state.settings:
            flashcard_settings = state.settings.get('flashcard', {})
            output.append(f"Flashcard settings: {flashcard_settings}")
            output.append(f"  - button_count: {flashcard_settings.get('button_count', 'NOT SET')}")
            output.append(f"  - autoplay: {flashcard_settings.get('autoplay', 'NOT SET')}")
            output.append(f"  - show_image: {flashcard_settings.get('show_image', 'NOT SET')}")
            output.append(f"  - show_stats: {flashcard_settings.get('show_stats', 'NOT SET')}")
            output.append(f"Auto-save: {state.settings.get('auto_save', 'NOT SET')}")
    else:
        output.append("\nNo container state found for container 7")
    
    output.append("\n" + "=" * 60)
    output.append("DEBUG: Testing settings update manually")
    output.append("=" * 60)
    
    if state:
        output.append(f"\nBefore update: {state.settings}")
        
        # Try to update with flag_modified
        from sqlalchemy.orm.attributes import flag_modified
        
        new_settings = dict(state.settings or {})
        if 'flashcard' not in new_settings:
            new_settings['flashcard'] = {}
        new_settings['flashcard']['button_count'] = 3
        new_settings['flashcard']['debug_timestamp'] = '2025-12-30 05:15:00'
        
        state.settings = new_settings
        flag_modified(state, 'settings')
        
        db.session.add(state)
        db.session.commit()
        
        # Re-fetch to verify
        db.session.expire_all()
        refreshed = UserContainerState.query.filter_by(container_id=7).first()
        
        output.append(f"After update: {refreshed.settings}")
        output.append(f"button_count after: {refreshed.settings.get('flashcard', {}).get('button_count', 'NOT SET')}")
    
    # Write to file
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print("Debug output written to debug_output.txt")

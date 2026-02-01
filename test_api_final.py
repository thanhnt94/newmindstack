from mindstack_app import create_app
from mindstack_app.modules.vocab_flashcard.engine.algorithms import get_flashcard_mode_counts
from mindstack_app.models import User, UserContainerState, db
import json

app = create_app()
with app.app_context():
    user_id = 1
    set_id = 4
    
    print(f"--- Testing Flashcard Modes for set {set_id} ---")
    try:
        modes = get_flashcard_mode_counts(user_id, set_id)
        
        essential_mode_ids = ['new_only', 'all_review', 'hard_only', 'mixed_srs', 'sequential']
        filtered_modes = [m for m in modes if m['id'] in essential_mode_ids]
        
        uc_state = UserContainerState.query.filter_by(
            user_id=user_id, 
            container_id=set_id
        ).first()
        
        settings = {}
        user_button_count = 4
        if uc_state and uc_state.settings:
            settings = uc_state.settings
            flashcard_settings = settings.get('flashcard', {})
            user_button_count = flashcard_settings.get('button_count', 4)

        result = {
            'success': True,
            'modes': filtered_modes,
            'user_button_count': user_button_count,
            'settings': settings
        }
        print("API Logic Result Success!")
        # print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n!!! ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

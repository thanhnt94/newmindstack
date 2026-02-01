# File: mindstack_app/modules/user_profile/routes/api.py
from flask import request
from flask_login import current_user
from mindstack_app.core.extensions import db
from .. import blueprint

@blueprint.route('/api/preferences', methods=['GET', 'POST'])
def manage_preferences():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'message': 'No data provided'}, 400
            
            current_user.last_preferences = data
            
            if 'flashcard_button_count' in data:
                pass
                
            db.session.commit()
            return {'success': True, 'message': 'Preferences saved successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}, 500
            
    prefs = current_user.last_preferences or {}
    
    default_prefs = {
        'flashcard_button_count': 4,
        'flashcard_show_image': True,
        'flashcard_autoplay_audio': True,
        'flashcard_show_stats': True,
        'quiz_question_count': 10,
        'auto_load_preferences': True
    }
    
    final_prefs = {**default_prefs, **prefs}
    
    return {'success': True, 'data': final_prefs}

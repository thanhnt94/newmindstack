# File: mindstack_app/modules/audio/routes/views.py
from flask import render_template, current_app, jsonify
from flask_login import login_required, current_user
from .. import audio_bp as blueprint

@blueprint.route('/studio', methods=['GET'])
@login_required
def admin_audio_studio():
    """
    Render the Audio Studio interface.
    """
    if current_user.user_role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    return render_template('admin/modules/audio/audio_studio.html', 
                           default_engine=current_app.config.get('AUDIO_DEFAULT_ENGINE', 'edge'),
                           default_voice_edge=current_app.config.get('AUDIO_DEFAULT_VOICE_EDGE', 'vi-VN-HoaiMyNeural'),
                           default_voice_gtts=current_app.config.get('AUDIO_DEFAULT_VOICE_GTTS', 'vi'),
                           voice_mapping=current_app.config.get('AUDIO_VOICE_MAPPING_GLOBAL', {})
                           )

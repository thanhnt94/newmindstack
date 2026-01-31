from flask import render_template, current_app, jsonify
from flask_login import login_required, current_user
from mindstack_app.modules.audio import blueprint

@blueprint.route('/admin/audio-studio', methods=['GET'])
@login_required
def admin_audio_studio():
    """
    Render the Audio Studio interface.
    """
    # Check admin permission if necessary
    if not current_user.is_authenticated: # Double check (login_required handles this)
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Ideally check for admin role
    # if current_user.role != 'admin': ...
    
    return render_template('admin/audio_studio.html', 
                           default_engine=current_app.config.get('AUDIO_DEFAULT_ENGINE', 'edge'),
                           default_voice_edge=current_app.config.get('AUDIO_DEFAULT_VOICE_EDGE', 'en-US-AriaNeural'),
                           default_voice_gtts=current_app.config.get('AUDIO_DEFAULT_VOICE_GTTS', 'en'),
                           voice_mapping=current_app.config.get('AUDIO_VOICE_MAPPING_GLOBAL', {})
                           )

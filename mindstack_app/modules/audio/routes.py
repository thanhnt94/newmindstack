import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from .services.audio_service import AudioService

# Define Blueprint
# We assume this will be registered at the app root '/' or we define routes with '/admin/...' prefix explicitly.
audio_bp = Blueprint('audio_bp', __name__)

@audio_bp.route('/admin/audio-studio', methods=['GET'])
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
                           default_voice_gtts=current_app.config.get('AUDIO_DEFAULT_VOICE_GTTS', 'en')
                           )

@audio_bp.route('/admin/audio/settings', methods=['POST'])
@login_required
def update_audio_settings():
    """Update default audio settings."""
    try:
        from mindstack_app.models import AppSettings, db
        data = request.get_json()
        
        updates = {
            'AUDIO_DEFAULT_ENGINE': data.get('default_engine'),
            'AUDIO_DEFAULT_VOICE_EDGE': data.get('default_voice_edge'),
            'AUDIO_DEFAULT_VOICE_GTTS': data.get('default_voice_gtts')
        }
        
        for key, value in updates.items():
            if value:
                setting = AppSettings.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    # Should be created by defaults, but just in case
                    setting = AppSettings(key=key, value=value, category='audio', data_type='string')
                    db.session.add(setting)
                    
        db.session.commit()
        
        # Reload config immediately
        if 'config_service' in current_app.extensions:
            current_app.extensions['config_service'].load_settings(force=True)
            
        return jsonify({'success': True, 'message': 'Cấu hình đã được lưu.'})
        
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Settings Update Error: {tb}")
        return jsonify({'success': False, 'error': str(e)}), 500

@audio_bp.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler for the Audio Blueprint."""
    tb = traceback.format_exc()
    current_app.logger.error(f"Audio Blueprint Error: {tb}")
    return jsonify({
        'success': False, 
        'error': str(e), 
        'traceback': tb
    }), 500

@audio_bp.route('/audio-debug-test', methods=['GET'])
async def debug_audio():
    """Temporary debug route - Open Access"""
    try:
        current_app.logger.info("Debug Route: Starting audio generation...")
        result = await AudioService.get_audio(
            text="Debug Audio System Check",
            engine="edge",
            voice="en-US-AriaNeural"
        )
        return jsonify(result)
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Debug Route Error: {tb}")
        return jsonify({'error': str(e), 'traceback': tb}), 500

@audio_bp.route('/admin/audio/process', methods=['POST'])
@login_required
async def process_audio():
    """
    API to generate audio via AudioService.
    """
    # try: block is redundant if we have bp handler, but good for custom logic.
    # I'll keep the inner logic simple.
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    text = data.get('text')
    engine = data.get('engine', 'edge')
    voice = data.get('voice')
    
    # Manual Mode Data
    is_manual = data.get('is_manual', False)
    target_dir = data.get('target_dir') if is_manual else None
    custom_filename = data.get('custom_filename') if is_manual else None
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
        
    # Call AudioService
    result = await AudioService.get_audio(
        text=text,
        engine=engine,
        voice=voice,
        target_dir=target_dir,
        custom_filename=custom_filename
    )
    
    if result.get('status') == 'error':
        return jsonify({'success': False, 'error': result.get('error')}), 500
        
    return jsonify({
        'success': True,
        'data': {
            'url': result.get('url'),
            'physical_path': result.get('physical_path'),
            'status': result.get('status')
        }
    })

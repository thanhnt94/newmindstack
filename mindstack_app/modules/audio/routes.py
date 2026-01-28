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
                           default_voice_gtts=current_app.config.get('AUDIO_DEFAULT_VOICE_GTTS', 'en'),
                           voice_mapping=current_app.config.get('AUDIO_VOICE_MAPPING_GLOBAL', {})
                           )

@audio_bp.route('/admin/audio/settings', methods=['POST'])
@login_required
def update_audio_settings():
    """Update default audio settings."""
    try:
        from mindstack_app.models import AppSettings, db
        data = request.get_json()
        
        import json
        
        updates = {
            'AUDIO_DEFAULT_ENGINE': data.get('default_engine'),
            'AUDIO_DEFAULT_VOICE_EDGE': data.get('default_voice_edge'),
            'AUDIO_DEFAULT_VOICE_GTTS': data.get('default_voice_gtts'),
            'AUDIO_VOICE_MAPPING_GLOBAL': json.dumps(data.get('voice_mapping')) if data.get('voice_mapping') else None
        }
        
        for key, value in updates.items():
            # Check if exists
            setting = AppSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
                if key == 'AUDIO_VOICE_MAPPING_GLOBAL':
                    setting.data_type = 'json'
                else:
                    setting.data_type = 'string'
                db.session.add(setting)
            else:
                 # Create new if missing
                 data_type = 'json' if key == 'AUDIO_VOICE_MAPPING_GLOBAL' else 'string'
                 setting = AppSettings(key=key, value=value, category='audio', data_type=data_type)
                 db.session.add(setting)
                 
        db.session.commit()
        
        # Refresh runtime config
        # IMPOTANT: We must parse JSON values back to objects before setting current_app.config
        for key, value in updates.items():
            if key == 'AUDIO_VOICE_MAPPING_GLOBAL' and isinstance(value, str):
                try:
                    current_app.config[key] = json.loads(value)
                except:
                    current_app.config[key] = {}
            else:
                 current_app.config[key] = value
            
        return jsonify({'status': 'success'})
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@audio_bp.route('/admin/audio/tasks/start', methods=['POST'])
@login_required
def start_audio_task():
    """Trigger background audio maintenance tasks."""
    try:
        data = request.get_json()
        task_name = data.get('task_name')
        
        # Import relevant task services (Local import to avoid circular dependency)
        from mindstack_app.models import BackgroundTask, db
        from mindstack_app.modules.flashcard.services import AudioService as FlashcardAudioService
        from mindstack_app.modules.quiz.individual.services.audio_service import QuizAudioService
        
        task = BackgroundTask.query.filter_by(task_name=task_name).first()
        if not task:
            task = BackgroundTask(task_name=task_name, status='idle')
            db.session.add(task)
            db.session.commit()
            
        if task.status == 'running':
            return jsonify({'success': False, 'message': 'Task is already running.'})
            
        task.status = 'running'
        task.message = 'Starting...'
        db.session.commit()
        
        # Dispatch
        try:
            if task_name == 'generate_audio_cache':
                # Use Flashcard service to generate cache
                svc = FlashcardAudioService()
                svc.generate_cache_for_all_cards(task) # This is synchronous in current impl
            elif task_name == 'clean_audio_cache':
                svc = FlashcardAudioService()
                svc.clean_orphan_audio_cache(task)
            elif task_name == 'transcribe_quiz_audio':
                svc = QuizAudioService()
                svc.transcribe_quiz_audio(task)
            else:
                 return jsonify({'success': False, 'message': 'Unknown task name.'})
                 
            return jsonify({'success': True, 'message': 'Task completed.'})
        except Exception as e:
            task.status = 'error'
            task.message = str(e)
            db.session.commit()
            raise e

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
        
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
    
    # Advanced: Auto Parse Voice Tags
    auto_voice_parsing = data.get('auto_voice_parsing', False)
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
        
    # Call AudioService
    result = await AudioService.get_audio(
        text=text,
        engine=engine,
        voice=voice,
        target_dir=target_dir,
        custom_filename=custom_filename,
        is_manual=is_manual,
        auto_voice_parsing=auto_voice_parsing
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

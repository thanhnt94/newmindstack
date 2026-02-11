# File: mindstack_app/modules/audio/routes/api.py
import traceback
import json
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from .. import audio_bp as blueprint
from ..services.audio_service import AudioService
from mindstack_app.models import AppSettings, db, BackgroundTask

@blueprint.route('/settings', methods=['POST'])
@login_required
def update_audio_settings():
    """Update default audio settings."""
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    try:
        data = request.get_json()
        
        updates = {
            'AUDIO_DEFAULT_ENGINE': data.get('default_engine'),
            'AUDIO_DEFAULT_VOICE_EDGE': data.get('default_voice_edge'),
            'AUDIO_DEFAULT_VOICE_GTTS': data.get('default_voice_gtts'),
            'AUDIO_VOICE_MAPPING_GLOBAL': json.dumps(data.get('voice_mapping')) if data.get('voice_mapping') else None
        }
        
        for key, value in updates.items():
            setting = AppSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
                setting.data_type = 'json' if key == 'AUDIO_VOICE_MAPPING_GLOBAL' else 'string'
                db.session.add(setting)
            else:
                 data_type = 'json' if key == 'AUDIO_VOICE_MAPPING_GLOBAL' else 'string'
                 setting = AppSettings(key=key, value=value, category='audio', data_type=data_type)
                 db.session.add(setting)
                 
        db.session.commit()
        
        # Refresh runtime config
        for key, value in updates.items():
            if key == 'AUDIO_VOICE_MAPPING_GLOBAL' and isinstance(value, str):
                try:
                    current_app.config[key] = json.loads(value)
                except:
                    current_app.config[key] = {}
            else:
                 current_app.config[key] = value
            
        return jsonify({'success': True, 'message': 'Cài đặt đã được lưu.'})

    except Exception as e:
        current_app.logger.error(f"Settings Update Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/tasks/start', methods=['POST'])
@login_required
def start_audio_task():
    """Trigger background audio maintenance tasks."""
    if current_user.user_role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    try:
        data = request.get_json()
        task_name = data.get('task_name')
        
        from mindstack_app.modules.vocabulary.flashcard.interface import FlashcardInterface
        from mindstack_app.modules.quiz.interface import transcribe_quiz_audio
        
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
        
        try:
            if task.task_name == 'regenerate_audio':
                item_ids = data.get('item_ids', []) # Assuming item_ids are passed in the request data
                audio_service = FlashcardInterface.get_audio_service_instance()
                audio_service.regenerate_audio_for_item_list(task, item_ids)
            elif task_name == 'generate_audio_cache':
                audio_service = FlashcardInterface.get_audio_service_instance()
                audio_service.generate_cache_for_all_cards(task)
            elif task_name == 'transcribe_quiz_audio':
                transcribe_quiz_audio(task)
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

@blueprint.route('/process', methods=['POST'])
@login_required
async def process_audio():
    """
    API to generate audio via AudioService.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    text = data.get('text')
    engine = data.get('engine', 'edge')
    voice = data.get('voice')
    is_manual = data.get('is_manual', False)
    target_dir = data.get('target_dir') if is_manual else None
    custom_filename = data.get('custom_filename') if is_manual else None
    auto_voice_parsing = data.get('auto_voice_parsing', False)
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
        
    from ..schemas import AudioRequestDTO
    request_dto = AudioRequestDTO(
        text=text,
        engine=engine,
        voice=voice,
        target_dir=target_dir,
        custom_filename=custom_filename,
        is_manual=is_manual,
        auto_voice_parsing=auto_voice_parsing
    )
    
    result = await AudioService.get_audio(request_dto)
    
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

@blueprint.route('/debug-test', methods=['GET'])
async def debug_audio():
    """Temporary debug route"""
    try:
        from ..schemas import AudioRequestDTO
        result = await AudioService.get_audio(AudioRequestDTO(
            text="Debug Audio System Check",
            engine="edge",
            voice="en-US-AriaNeural"
        ))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import json
from datetime import datetime
from flask import current_app
from mindstack_app.core.extensions import db
from mindstack_app.models import LearningContainer, LearningItem
from ..models import GenerationLog
from ..schemas import TextGenerationSchema, AudioGenerationSchema, ImageGenerationSchema
from .. import tasks
from .. import signals
from ..exceptions import InvalidRequestError

def _dispatch_task(request_type, data, schema_class):
    """
    SINGLE TASK DISPATCHER: Validates, logs, and immediately starts a thread.
    Used for single manual tests.
    """
    # 1. Validate Input
    schema = schema_class()
    errors = schema.validate(data)
    if errors:
        raise InvalidRequestError(f"Validation failed: {errors}")
    clean_data = schema.load(data)
    
    # 2. Create Log
    log = GenerationLog(
        request_type=request_type,
        requester_module=clean_data.get('requester_module', 'unknown'),
        session_id=clean_data.get('session_id'),
        session_name=clean_data.get('session_name'),
        item_id=clean_data.get('item_id'),
        item_title=clean_data.get('item_title'),
        delay_seconds=0, # Single tasks run immediately
        input_payload=json.dumps(clean_data),
        status='pending'
    )
    db.session.add(log)
    db.session.commit()
    
    # 3. Run immediately
    app = current_app._get_current_object()
    tasks.run_in_background(app, log.id, delay_seconds=clean_data.get('delay_seconds', 0))
    
    return log

def dispatch_text_generation(data):
    return _dispatch_task('text', data, TextGenerationSchema)

def dispatch_audio_generation(data):
    return _dispatch_task('audio', data, AudioGenerationSchema)

def dispatch_image_generation(data):
    return _dispatch_task('image', data, ImageGenerationSchema)

def get_log_status(log_id):
    return GenerationLog.query.get(log_id)

def dispatch_bulk_generation(container_id, options, requester_module):
    """
    BULK DISPATCHER: Creates all logs first, then starts a single sequential runner.
    """
    container = LearningContainer.query.get(container_id)
    if not container:
        raise InvalidRequestError(f"Container ID {container_id} not found.")
        
    items = LearningItem.query.filter_by(container_id=container_id).all()
    
    tasks_created = 0
    delay_per_item = int(options.get('delay_seconds', 5))
    session_id = f"bulk_{container_id}_{int(datetime.utcnow().timestamp())}"
    session_name = options.get('batch_name') or f"Bulk: {container.title}"
    
    gen_audio = options.get('gen_audio', False)
    gen_ai_content = options.get('gen_ai_content', False)
    overwrite = options.get('overwrite', False)
    
    # --- Phase 1: Create all Logs (Pending) ---
    for item in items:
        content = item.content or {}
        
        # Determine sides
        sides_to_process = []
        if item.item_type == 'FLASHCARD':
            front_text = content.get('front_audio_content') or content.get('front') or content.get('term') or content.get('question')
            back_text = content.get('back_audio_content') or content.get('back') or content.get('definition') or content.get('answer')
            if front_text: sides_to_process.append(('front', front_text))
            if back_text: sides_to_process.append(('back', back_text))
        elif item.item_type == 'QUIZ_MCQ':
            quiz_text = content.get('front_audio_content') or content.get('question')
            if quiz_text: sides_to_process.append(('front', quiz_text))
        
        common_payload = {
            "requester_module": requester_module,
            "session_id": session_id,
            "session_name": session_name,
            "item_id": item.item_id,
            "container_id": container_id,
            "item_title": sides_to_process[0][1][:200] if sides_to_process else f"Item {item.item_id}"
        }

        # Audio Logs
        if gen_audio:
            for side, text in sides_to_process:
                audio_key = f"{side}_audio_url"
                has_audio = (item.custom_data and item.custom_data.get(audio_key)) or (content.get(audio_key))
                
                if not has_audio or overwrite:
                    payload = {
                        **common_payload,
                        "text": text,
                        "voice_id": options.get('voice_id', 'default'),
                        "side": side,
                        "custom_filename": f"{side}_{item.item_id}.mp3",
                        # We don't set delay here anymore, runner handles it
                    }
                    
                    log = GenerationLog(
                        request_type='audio',
                        requester_module=requester_module,
                        session_id=session_id,
                        session_name=session_name,
                        item_id=item.item_id,
                        item_title=f"[{side.upper()}] {text[:50]}...",
                        input_payload=json.dumps(payload),
                        status='pending'
                    )
                    db.session.add(log)
                    tasks_created += 1
                
        # AI Logs
        if gen_ai_content:
            primary_text = content.get('front') or content.get('question')
            if primary_text:
                payload = {
                    **common_payload,
                    "prompt": f"Explain the term '{primary_text}' and give 3 examples.",
                }
                log = GenerationLog(
                    request_type='text',
                    requester_module=requester_module,
                    session_id=session_id,
                    session_name=session_name,
                    item_id=item.item_id,
                    item_title=f"[AI] {primary_text[:50]}...",
                    input_payload=json.dumps(payload),
                    status='pending'
                )
                db.session.add(log)
                tasks_created += 1

    db.session.commit()

    # --- Phase 2: Start Master Runner ---
    if tasks_created > 0:
        app = current_app._get_current_object()
        tasks.start_session_runner(app, session_id, delay_per_item)

    return {
        "tasks_created": tasks_created,
        "session_id": session_id,
        "container_title": container.title
    }

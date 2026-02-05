import json
from datetime import datetime
from flask import current_app
from mindstack_app.core.extensions import db
from ..models import GenerationLog
from ..schemas import TextGenerationSchema, AudioGenerationSchema, ImageGenerationSchema
from .. import tasks
from .. import signals
from ..exceptions import InvalidRequestError

def _dispatch_task(request_type, data, schema_class):
    """Internal helper to validate, log, and queue a task."""
    
    # 1. Validate Input
    schema = schema_class()
    errors = schema.validate(data)
    if errors:
        raise InvalidRequestError(f"Validation failed: {errors}")
    
    clean_data = schema.load(data)
    
    # 2. Create Audit Log (Pending)
    log = GenerationLog(
        request_type=request_type,
        requester_module=clean_data.get('requester_module', 'unknown'),
        session_id=clean_data.get('session_id'),
        delay_seconds=clean_data.get('delay_seconds', 0),
        input_payload=json.dumps(clean_data),
        status='pending'
    )
    db.session.add(log)
    db.session.commit()
    
    # 3. Queue Background Task (Threading)
    # Using simple threading to avoid heavy Celery dependency
    delay = clean_data.get('delay_seconds', 0)
    
    # We need to capture the real app object (not the proxy) to pass to the thread
    app = current_app._get_current_object()
    tasks.run_in_background(app, log.id, delay_seconds=delay)
    
    # 4. Update Log with Task ID (Simulation)
    log.task_id = f"thread-{log.id}"
    db.session.commit()
    
    # 5. Emit Signal (Optional, useful for real-time UI updates)
    signals.generation_queued.send(current_app._get_current_object(), log_id=log.id)
    
    return log

def dispatch_text_generation(data):
    return _dispatch_task('text', data, TextGenerationSchema)

def dispatch_audio_generation(data):
    return _dispatch_task('audio', data, AudioGenerationSchema)

def dispatch_image_generation(data):
    return _dispatch_task('image', data, ImageGenerationSchema)

def get_log_status(log_id):
    return GenerationLog.query.get(log_id)

import json
import logging
import time
from datetime import datetime
from threading import Thread
from flask import current_app
from mindstack_app.core.extensions import db
from .models import GenerationLog
from .engine.core import ContentEngine
from . import signals

logger = logging.getLogger(__name__)

def run_in_background(app, log_id, delay_seconds=0):
    """
    Helper to run task in a separate thread with app context.
    """
    def task_wrapper():
        with app.app_context():
            # Handle delay for rate limiting
            if delay_seconds > 0:
                logger.info(f"Task: Sleeping for {delay_seconds}s before processing Log ID {log_id}")
                time.sleep(delay_seconds)
                
            process_generation_task(log_id)

    thread = Thread(target=task_wrapper)
    thread.start()
    return thread

def process_generation_task(log_id):
    """
    Worker function to execute the content generation logic.
    """
    logger.info(f"Task: Starting generation for Log ID {log_id}")
    
    # 1. Retrieve Context
    log = GenerationLog.query.get(log_id)
    if not log:
        logger.error(f"Task: Log ID {log_id} not found.")
        return
    
    log.status = 'processing'
    db.session.commit()
    
    try:
        # 2. Initialize Engine
        api_keys = {
            'openai': current_app.config.get('CONTENT_GEN_OPENAI_API_KEY'),
            'elevenlabs': current_app.config.get('CONTENT_GEN_ELEVENLABS_API_KEY'),
            'stable_diffusion': current_app.config.get('CONTENT_GEN_STABLE_DIFFUSION_KEY')
        }
        engine = ContentEngine(api_keys)
        
        # 3. Parse Input
        inputs = json.loads(log.input_payload)
        
        # Remove metadata not needed by engine (like session_id, delay, etc.)
        inputs.pop('requester_module', None)
        inputs.pop('session_id', None)
        inputs.pop('delay_seconds', None)
            
        # 4. Execute Engine Logic
        result = None
        if log.request_type == 'text':
            result = engine.generate_text(**inputs)
        elif log.request_type == 'audio':
            result = engine.generate_audio(**inputs)
        elif log.request_type == 'image':
            result = engine.generate_image(**inputs)
        else:
            raise ValueError(f"Unknown request type: {log.request_type}")
            
        # 5. Success Handling
        log.output_result = json.dumps(result)
        log.status = 'completed'
        log.completed_at = datetime.utcnow()
        if result and 'usage' in result:
             # Basic cost tracking if provider returns usage
            log.cost_tokens = result['usage'].get('total_tokens', 0)
            
        db.session.commit()
        
        # Emit Signal
        signals.generation_completed.send(current_app._get_current_object(), log_id=log.id, result=result)
        logger.info(f"Task: Generation completed for Log ID {log_id}")

    except Exception as e:
        # 6. Failure Handling
        logger.error(f"Task: Generation failed for Log ID {log_id}. Error: {str(e)}")
        # Re-query log to ensure session is attached if connection was lost
        log = GenerationLog.query.get(log_id) 
        if log:
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            db.session.commit()
        
        signals.generation_failed.send(current_app._get_current_object(), log_id=log.id, error=str(e))
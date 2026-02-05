import json
import logging
import time
from datetime import datetime
from threading import Thread
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified
from mindstack_app.core.extensions import db
from mindstack_app.models import LearningItem, LearningContainer
from .models import GenerationLog
from .engine.core import ContentEngine
from . import signals

logger = logging.getLogger(__name__)

def run_in_background(app, log_id, delay_seconds=0):
    """(Deprecated for Bulk) Keep for single tasks."""
    def task_wrapper():
        with app.app_context():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            process_generation_task(log_id)
    thread = Thread(target=task_wrapper)
    thread.start()
    return thread

def start_session_runner(app, session_id, delay_per_item):
    """
    Master Worker: Runs tasks sequentially with delay AFTER each completion.
    """
    def runner():
        with app.app_context():
            logger.info(f"Session Runner: Started for {session_id}")
            
            # Get all pending tasks for this session, ordered by creation (or ID)
            # We fetch IDs only to keep memory low, then fetch objects one by one
            task_ids = [r.id for r in db.session.query(GenerationLog.id).filter_by(
                session_id=session_id, status='pending'
            ).order_by(GenerationLog.id).all()]
            
            total = len(task_ids)
            logger.info(f"Session Runner: Found {total} tasks to process.")
            
            for idx, log_id in enumerate(task_ids):
                # 0. Ensure fresh data (crucial for detecting Stop signal from API thread)
                db.session.commit()

                # 1. Check Global Stop Signal (Check specific task or generic session flag)
                # Since we don't have a session-level table, we check the first remaining task's stop flag
                # or rely on process_generation_task to handle it.
                
                # Check if this specific task was cancelled before we start
                current_log = GenerationLog.query.get(log_id)
                if not current_log or current_log.stop_requested:
                    logger.info("Session Runner: Stop signal detected.")
                    break
                
                # 2. Process the task (Synchronously wait for it to finish)
                process_generation_task(log_id)
                
                # 3. Wait BEFORE the next task (if not the last one)
                if idx < total - 1 and delay_per_item > 0:
                    next_log_id = task_ids[idx + 1]
                    # Check stop signal again during sleep
                    for _ in range(delay_per_item):
                        db.session.commit() # End previous transaction to see external updates
                        
                        # We MUST check the NEXT task because the current one is likely COMPLETED
                        # and the Stop API only flags 'pending'/'processing' tasks.
                        next_task = GenerationLog.query.get(next_log_id)
                        if next_task and (next_task.stop_requested or next_task.status == 'failed'):
                            logger.info(f"Session Runner: Stop detected on next task {next_log_id}")
                            break 
                        time.sleep(1)
                        
    thread = Thread(target=runner)
    thread.start()
    return thread

def _ensure_container_media_folder(container, media_type):
    """
    Replicated logic from vocab_flashcard to resolve media folder.
    """
    attr_name = f"media_{media_type}_folder"
    existing = getattr(container, attr_name, None)
    if existing:
        return existing
    
    type_slug = (container.container_type or "").lower()
    if type_slug.endswith("_set"):
        type_slug = type_slug[:-4]
    type_slug = type_slug.replace("_", "-") or "container"
    
    default_folder = f"{type_slug}/{container.container_id}/{media_type}"
    
    # Save back to container settings if possible, or just use default
    # Note: running in thread context, be careful with session
    try:
        setattr(container, attr_name, default_folder)
        db.session.add(container)
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    return default_folder

def process_generation_task(log_id):
    """
    Worker function to execute the content generation logic.
    """
    logger.info(f"Task: Starting generation for Log ID {log_id}")
    
    log = GenerationLog.query.get(log_id)
    if not log or log.status in ['completed', 'failed']:
        return
    
    if log.stop_requested:
        log.status = 'failed'
        log.error_message = "Stopped by user."
        db.session.commit()
        return

    log.status = 'processing'
    db.session.commit()
    
    try:
        engine = ContentEngine()
        inputs = json.loads(log.input_payload)
        
        container_id = inputs.get('container_id')
        item_id = log.item_id
        side = inputs.get('side', 'front') # Default to front if missing
        
        # Path Resolution Logic for Audio
        if log.request_type == 'audio' and container_id and item_id:
            container = LearningContainer.query.get(container_id)
            if container:
                # Get dynamic folder from container config
                relative_folder = _ensure_container_media_folder(container, 'audio')
                target_dir = f"uploads/{relative_folder}"
                
                # Create directory physically (Crucial fix for FileNotFoundError)
                import os
                abs_target_dir = os.path.join(current_app.root_path, target_dir) if not os.path.isabs(target_dir) else target_dir
                os.makedirs(abs_target_dir, exist_ok=True)
                
                inputs['target_dir'] = target_dir
                inputs['custom_filename'] = f"{side}_{item_id}.mp3"
        
        context_ref = f"ITEM_{item_id}" if item_id else None
            
        # Execute Engine
        result = None
        if log.request_type == 'text':
            result = engine.generate_text(context_ref=context_ref, **inputs)
        elif log.request_type == 'audio':
            result = engine.generate_audio(**inputs)
        elif log.request_type == 'image':
            result = engine.generate_image(**inputs)
        else:
            raise ValueError(f"Unknown request type: {log.request_type}")
            
        # Check Stop Signal
        db.session.refresh(log)
        if log.stop_requested:
            log.status = 'failed'
            log.error_message = "Stopped by user during processing."
            db.session.commit()
            return

        # Save Result
        log.output_result = json.dumps(result)
        # Store physical path in log for easy debugging
        if 'physical_path' in result:
            logger.info(f"Task: File created at {result['physical_path']}")
            
        log.status = 'completed'
        log.completed_at = datetime.utcnow()
        
        # Update Learning Item
        if item_id:
            item = LearningItem.query.get(item_id)
            if item:
                if log.request_type == 'audio' and result.get('status') == 'success':
                    # Result path might be absolute or relative, ensure we store relative to media root
                    # Logic: We know exactly where we told it to save.
                    
                    # If we used custom filename, construct the storage value manually to be safe
                    if container_id and 'custom_filename' in inputs:
                        # Re-fetch folder to be sure
                        container = LearningItem.query.get(item_id).container
                        folder = _ensure_container_media_folder(container, 'audio')
                        stored_value = f"{folder}/{inputs['custom_filename']}"
                    else:
                        # Fallback logic: Try to reconstruct path even if custom_filename missing
                        # This fixes cases where fallback returns just filename
                        try:
                            container = LearningItem.query.get(item_id).container
                            if container:
                                folder = _ensure_container_media_folder(container, 'audio')
                                filename = os.path.basename(result.get('file_path', ''))
                                stored_value = f"{folder}/{filename}"
                            else:
                                stored_value = result.get('file_path')
                        except:
                            stored_value = result.get('file_path')

                    if not item.content: item.content = {}
                    
                    # Update Content (Standard)
                    item.content[f'{side}_audio_url'] = stored_value
                    
                    # Update Custom Data (Backup/Legacy)
                    if not item.custom_data: item.custom_data = {}
                    item.custom_data[f'{side}_audio_url'] = stored_value
                    
                    flag_modified(item, 'content')
                    flag_modified(item, 'custom_data')
                    
                elif log.request_type == 'text' and 'text' in result:
                    item.ai_explanation = result['text']
                
                db.session.add(item)
        
        db.session.commit()
        signals.generation_completed.send(current_app._get_current_object(), log_id=log.id, result=result)

    except Exception as e:
        logger.error(f"Task: Generation failed for Log ID {log_id}. Error: {str(e)}")
        log = GenerationLog.query.get(log_id) 
        if log:
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            db.session.commit()
        signals.generation_failed.send(current_app._get_current_object(), log_id=log.id, error=str(e))
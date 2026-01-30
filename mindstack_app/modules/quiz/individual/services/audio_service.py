
import logging
import os
from mindstack_app.core.extensions import db
from mindstack_app.models import LearningContainer, LearningItem, BackgroundTask
from mindstack_app.modules.audio.services.audio_service import AudioService

logger = logging.getLogger(__name__)

class QuizAudioService:
    """
    Manages audio operations for Quiz items: specifically Speech-to-Text (STT) transcription.
    """
    def __init__(self):
        # We use static methods from AudioService now
        pass

    def transcribe_quiz_audio(self, task, container_ids=None):
        """
        Scans quiz items for audio content and uses VoiceEngine to transcribe it to text.
        Updates the 'transcript' (or similar field) in the learning item's content.
        """
        log_prefix = f"[{task.task_name}]"
        logger.info(f"{log_prefix} Starting quiz transcription task.")
        
        try:
            # 1. Determine Scope
            scope_label = "all Quiz Sets"
            
            normalized_container_ids = None
            if container_ids:
                if not isinstance(container_ids, (list, tuple)):
                    container_ids = [container_ids]
                try:
                    normalized_container_ids = [int(cid) for cid in container_ids if cid]
                except ValueError:
                    pass

            query = LearningItem.query.filter(LearningItem.item_type == 'QUIZ_QUESTION')
            
            # Filter specifically for items HAVING audio but MISSING transcript/text
            # Note: Checking JSON content in SQL is tricky without specific JSON operators.
            # We'll fetch candidates and filter in Python for simplicity/compatibility.
            # We assume audio is stored in content['audio_url'] or similar, and text in content['question'] or content['transcript']
            # Let's assume user wants to populate 'question' text from audio if empty, or a specific 'transcript' field.
            # For now, let's look for items with 'audio_url' property.
            
            if normalized_container_ids:
                 query = query.filter(LearningItem.container_id.in_(normalized_container_ids))
                 scope_label = f"selected Quiz Sets ({len(normalized_container_ids)})"

            candidates = query.all()
            
            items_to_process = []
            for item in candidates:
                content = item.content or {}
                # Hypothetical structure: look for audio path. 
                # Adjust key 'audio_url' or 'audio_path' based on actual data structure.
                # Assuming 'question_audio' based on common patterns or 'audio_url'.
                # Let's check for common audio keys.
                audio_path = content.get('question_audio') or content.get('audio_url')
                
                # We process if there is audio AND (missing transcript OR we want to force update?)
                # Let's assume we only process if there's no text explanation or specific transcript field.
                # Let's say we put result in 'audio_transcript'
                if audio_path and not content.get('audio_transcript'):
                     items_to_process.append((item, audio_path))

            task.total = len(items_to_process)
            task.progress = 0
            task.status = 'running'
            
            if task.total == 0:
                task.message = f"No quiz items with untranscribed audio found in {scope_label}."
                task.status = 'completed'
                db.session.commit()
                return

            task.message = f"Found {task.total} items to transcribe in {scope_label}."
            db.session.commit()
            
            success_count = 0
            
            # 2. Process
            base_upload_path = os.path.join(os.getcwd(), 'mindstack_app', 'static') # Adjust base path as needed
            
            for item, rel_audio_path in items_to_process:
                db.session.refresh(task)
                if task.stop_requested:
                    break
                
                # Resolve absolute path. Audio paths in DB are usually relative to static or uploads.
                # Try to find the file.
                full_path = rel_audio_path
                if not os.path.exists(full_path):
                    # Try probing common roots
                    potential_path = os.path.join(base_upload_path, rel_audio_path.lstrip('/\\'))
                    if os.path.exists(potential_path):
                        full_path = potential_path
                
                if not os.path.exists(full_path):
                    logger.warning(f"{log_prefix} Audio file not found for item {item.item_id}: {rel_audio_path}")
                    task.progress += 1
                    continue
                
                try:
                    task.message = f"Transcribing item {item.item_id} ({task.progress + 1}/{task.total})..."
                    db.session.commit()
                    
                    transcript = AudioService.speech_to_text(full_path, lang='vi-VN') # Defaulting to VN
                    
                    if transcript:
                        # Update Item Content
                        # We need to clone content to trigger SQLAlchemy mutation detection on JSON
                        new_content = dict(item.content)
                        new_content['audio_transcript'] = transcript
                        
                        # Optionally populate question text if empty?
                        # if not new_content.get('question'):
                        #     new_content['question'] = transcript
                            
                        item.content = new_content
                        flag_modified(item, "content") # Explicitly flag modified if needed
                        db.session.add(item)
                        db.session.commit()
                        success_count += 1
                        logger.info(f"{log_prefix} Transcribed item {item.item_id}: {transcript[:30]}...")
                    
                except Exception as e:
                    logger.error(f"{log_prefix} Error transcribing item {item.item_id}: {e}")
                
                task.progress += 1
                db.session.commit()

            task.status = 'completed'
            task.message = f"Completed. Transcribed {success_count}/{task.total} items."
            task.stop_requested = False
            task.is_enabled = False # Auto-disable after run? Or keep enabled. Let's keep existing pattern.
            db.session.commit()

        except Exception as e:
            task.status = 'error'
            task.message = f"Fatal error: {str(e)}"
            logger.error(f"{log_prefix} {task.message}", exc_info=True)
            db.session.commit()

from sqlalchemy.orm.attributes import flag_modified

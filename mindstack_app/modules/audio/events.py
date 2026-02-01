from mindstack_app.core.signals import content_changed
from flask import current_app
import asyncio
from .services.audio_service import AudioService
from mindstack_app.models import LearningItem, db

@content_changed.connect
def handle_audio_content_change(sender, **kwargs):
    """
    Listen for content changes and trigger audio regeneration if needed.
    """
    content_type = kwargs.get('content_type')
    content_id = kwargs.get('content_id')
    
    if content_type != 'item':
        return

    # Trigger async task if in app context or use current_app for background check
    # Note: Flask's blinker signals are synchronous. For long tasks, use a thread or task queue.
    # For now, we'll just check if audio regeneration is requested in payload.
    
    payload = kwargs.get('payload', {})
    if payload.get('regenerate_audio'):
        # In a real production app, this would be an Celery task.
        # For MindStack simple setup, we might use a thread or just a safe async call if possible.
        
        # We need the item to know what to speak
        item = LearningItem.query.get(content_id)
        if not item or item.item_type != 'FLASHCARD':
            return
            
        current_app.logger.info(f"[AudioEvent] Triggering audio regeneration for item {content_id}")
        
        # Simple thread-based fire and forget for MindStack
        import threading
        def run_regen(app_context):
            with app_context:
                # We need to run the async AudioService.get_audio in a loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                front_text = item.content.get('front', '')
                back_text = item.content.get('back', '')
                
                # We use the generic logic to determine paths or just rely on AudioService
                # to hash based on the new content.
                from .schemas import AudioRequestDTO
                if front_text:
                    loop.run_until_complete(AudioService.get_audio(AudioRequestDTO(text=front_text, is_manual=True)))
                if back_text:
                    loop.run_until_complete(AudioService.get_audio(AudioRequestDTO(text=back_text, is_manual=True)))
                    
        thread = threading.Thread(target=run_regen, args=(current_app.app_context(),))
        thread.start()

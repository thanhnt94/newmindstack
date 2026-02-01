from mindstack_app.core.signals import content_changed
from flask import current_app
from mindstack_app.models import LearningItem, db
import threading

@content_changed.connect
def handle_ai_content_change(sender, **kwargs):
    """
    Listen for content changes and trigger AI translation/explanation if needed.
    """
    content_type = kwargs.get('content_type')
    content_id = kwargs.get('content_id')
    payload = kwargs.get('payload', {})
    
    if content_type != 'item' or not payload.get('ai_process'):
        return

    item = LearningItem.query.get(content_id)
    if not item:
        return

    current_app.logger.info(f"[AIEvent] Triggering AI processing for item {content_id}")
    
    def run_ai_task(app_context):
        with app_context:
            try:
                from mindstack_app.modules.AI.services.gemini_service import GeminiService
                
                # Example: Auto-explain if it's a flashcard and has no explanation
                if item.item_type == 'FLASHCARD' and (not item.ai_explanation or payload.get('force_ai')):
                    front = item.content.get('front', '')
                    back = item.content.get('back', '')
                    prompt = f"Explain this vocabulary: {front} ({back}). Keep it concise."
                    
                    result = GeminiService.generate_content(prompt)
                    if result and result.get('text'):
                        item.ai_explanation = result['text']
                        db.session.commit()
                        current_app.logger.info(f"[AIEvent] Updated explanation for item {content_id}")
            except Exception as e:
                current_app.logger.error(f"[AIEvent] Error: {e}")

    thread = threading.Thread(target=run_ai_task, args=(current_app.app_context(),))
    thread.start()

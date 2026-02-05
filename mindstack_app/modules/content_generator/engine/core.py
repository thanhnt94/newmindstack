import logging
import asyncio
from mindstack_app.modules.audio.interface import AudioInterface
from mindstack_app.modules.AI.interface import AIInterface

logger = logging.getLogger(__name__)

class ContentEngine:
    """
    Core Logic Engine for Content Generation.
    Integrates with existing system modules (Audio, AI).
    """
    def __init__(self, api_keys: dict = None):
        # Existing modules manage their own keys/configs
        pass

    def generate_text(self, prompt, context_ref=None, **kwargs):
        """
        Wrapper for Text Generation using AI module.
        """
        logger.info(f"Engine: Calling AI module for: {prompt[:50]}...")
        
        result = AIInterface.generate_content(prompt, feature="explanation", context_ref=context_ref)
        
        if result.success:
            return {
                "text": result.content,
                "status": "success"
            }
        else:
            raise Exception(f"AI Module Error: {result.error}")

    def generate_audio(self, text, voice_id=None, target_dir=None, custom_filename=None, **kwargs):
        """
        Wrapper for Audio Generation using Audio module.
        Supports auto-voice parsing and custom storage.
        """
        logger.info(f"Engine: Calling Audio module for text: {text[:50]}...")
        
        try:
            # Create a new event loop for this thread to run the async audio service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Use auto_voice_parsing=True to enable smart multi-voice generation
            result = loop.run_until_complete(AudioInterface.generate_audio(
                text=text,
                voice=voice_id,
                engine=kwargs.get('engine', 'edge'),
                target_dir=target_dir,
                custom_filename=custom_filename,
                is_manual=True, # Force regenerate as requested by user
                auto_voice_parsing=True 
            ))
            loop.close()
            
            if result.status in ['success', 'generated', 'exists'] and result.url:
                return {
                    "file_path": result.url, # URL to be saved in DB
                    "physical_path": result.physical_path,
                    "status": "success"
                }
            else:
                error_msg = result.error or "Unknown error from Audio Service"
                raise Exception(f"Audio Module Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Engine: Audio generation failed: {e}")
            raise e

    def generate_image(self, prompt, size="1024x1024", **kwargs):
        """
        Placeholder for Image Generation.
        """
        return {
            "file_path": "uploads/placeholder_image.png",
            "status": "simulated"
        }

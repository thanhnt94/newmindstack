import logging
import threading
from mindstack_app.models import AppSettings
from ..engines.gemini_client import GeminiClient
from ..engines.hybrid_client import HybridAIClient

logger = logging.getLogger(__name__)

class AIServiceManager:
    _lock = threading.Lock()
    _service_instance = None
    _last_config = {}

    @classmethod
    def get_service(cls) -> HybridAIClient:
        """
        Returns a configured HybridAIClient instance.
        """
        # Get latest configuration
        config = {
            'provider': AppSettings.get('AI_PROVIDER', 'gemini'),
            'gemini_model': AppSettings.get('GEMINI_MODEL', 'gemini-2.0-flash-lite-001'),
            'hf_model': AppSettings.get('HUGGINGFACE_MODEL', 'google/gemma-7b-it')
        }

        with cls._lock:
            if cls._service_instance is None or cls._last_config != config:
                logger.info(f"AIServiceManager: Initializing AI Service with {config}")
                cls._service_instance = HybridAIClient(
                    primary_provider=config['provider'],
                    gemini_model=config['gemini_model'],
                    hf_model=config['hf_model']
                )
                cls._last_config = config
        
        return cls._service_instance

def get_ai_service():
    """Helper to get the current AI service."""
    return AIServiceManager.get_service()

import logging
from typing import Tuple, Optional
from .gemini_client import GeminiClient
from .huggingface_client import HuggingFaceClient

logger = logging.getLogger(__name__)

class HybridAIClient:
    """
    Stateless proxy for multiple AI providers with automatic fallback.
    """
    def __init__(self, primary_provider: str = 'gemini', gemini_model: str = None, hf_model: str = None):
        self.primary_provider = primary_provider
        
        # Child clients are also stateless
        self.gemini_client = GeminiClient(model_name=gemini_model)
        self.hf_client = HuggingFaceClient(model_name=hf_model)
        
        if primary_provider == 'huggingface':
            self.execution_order = [
                ('huggingface', self.hf_client),
                ('gemini', self.gemini_client)
            ]
        else:
            self.execution_order = [
                ('gemini', self.gemini_client),
                ('huggingface', self.hf_client)
            ]

    def generate_content(self, prompt: str, feature: str = 'default', context_ref: str = 'N/A', user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Try primary provider, fallback to others on failure.
        """
        errors = []
        
        for provider_name, client in self.execution_order:
            try:
                success, result = client.generate_content(prompt, feature, context_ref, user_id)
                if success:
                    return True, result
                errors.append(f"{provider_name}: {result}")
            except Exception as e:
                logger.error(f"HybridAI: {provider_name} critical failure: {e}")
                errors.append(f"{provider_name} (critical): {e}")

        return False, "Retry overflow. Details: " + " | ".join(errors)

    @staticmethod
    def get_available_models():
        return {'success': False, 'message': 'Hybrid client does not support global model listing.'}

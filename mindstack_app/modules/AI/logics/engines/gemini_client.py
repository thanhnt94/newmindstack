import time
import logging
from typing import Tuple, Optional

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    genai = None

from mindstack_app.core.ai_resource_manager import AiResourceManager

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Stateless worker for Gemini API interactions.
    Does not depend on DB or Flask Context directly.
    """
    
    def __init__(self, model_name: str = 'gemini-2.0-flash-lite-001'):
        if not genai:
            raise ImportError("Google Generative AI library not installed.")
        
        self.model_name = model_name
        self.resource_manager = AiResourceManager.get_manager('gemini')

    def generate_content(self, prompt: str, feature: str = 'default', context_ref: str = 'N/A', user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Generates content using the configured model fallback logic.
        """
        raw_models = self.model_name.split(',')
        models_to_try = [m.strip() for m in raw_models if m.strip()]
        
        last_error = "No models configured"

        for model_chk in models_to_try:
            success, result = self._try_model(model_chk, prompt, feature, context_ref, user_id)
            if success:
                return True, result
            last_error = result
            
        return False, f"All models failed. Last error: {last_error}"

    def _try_model(self, model_target: str, prompt: str, feature: str, context_ref: str, user_id: Optional[int]) -> Tuple[bool, str]:
        max_retries = 3
        last_err = None

        for attempt in range(max_retries):
            start_time = time.time()
            key_id, key_value = self.resource_manager.get_key()
            
            if not key_value:
                return False, "No available API keys."

            try:
                genai.configure(api_key=key_value)
                model = genai.GenerativeModel(model_target)
                
                # Mocking token counts as standard Gemini doesn't always return them simply in all parts
                # In a real scenario, we'd use response.usage_metadata
                response = model.generate_content(prompt)
                
                if response.parts:
                    content = response.text
                    duration = int((time.time() - start_time) * 1000)
                    
                    # Estimate tokens (simplistic)
                    in_tokens = len(prompt) // 4
                    out_tokens = len(content) // 4
                    
                    self.resource_manager.log_usage(
                        model_name=model_target,
                        key_id=key_id,
                        feature=feature,
                        input_tokens=in_tokens,
                        output_tokens=out_tokens,
                        duration_ms=duration,
                        status='success',
                        context_ref=context_ref,
                        user_id=user_id
                    )
                    return True, content
                
                last_err = "Empty response parts"
                
            except google_exceptions.ResourceExhausted:
                logger.warning(f"Key {key_id} exhausted.")
                self.resource_manager.force_refresh()
                # If we get 429, we might want to try another key immediately
                continue
                
            except google_exceptions.PermissionDenied:
                logger.error(f"Key {key_id} permission denied.")
                self.resource_manager.mark_key_exhausted(key_id)
                continue
                
            except Exception as e:
                last_err = str(e)
                logger.error(f"Gemini API error: {e}")
                self.resource_manager.log_usage(
                    model_name=model_target,
                    key_id=key_id,
                    feature=feature,
                    status='error',
                    error_message=last_err,
                    context_ref=context_ref,
                    user_id=user_id
                )
                break # Break retries on unknown errors
                
        return False, last_err or "Retry limit reached"

    @staticmethod
    def get_available_models():
        """Kernel-agnostic model listing."""
        # This still needs a key, but for simplicity of the refactor 
        # we can keep it as is or move to manager
        if not genai: return []
        try:
            mgr = AiResourceManager.get_manager('gemini')
            _, val = mgr.get_key()
            if not val: return []
            genai.configure(api_key=val)
            return [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            return []

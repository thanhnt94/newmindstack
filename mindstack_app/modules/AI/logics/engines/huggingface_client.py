import time
import logging
from typing import Tuple, Optional

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

from mindstack_app.core.ai_resource_manager import AiResourceManager

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    """
    Stateless worker for Hugging Face Inference API.
    """
    def __init__(self, model_name: str = 'google/gemma-7b-it'):
        if not InferenceClient:
            raise ImportError("huggingface_hub library not installed.")
        
        self.model_name = model_name
        self.resource_manager = AiResourceManager.get_manager('huggingface')

    def generate_content(self, prompt: str, feature: str = 'default', context_ref: str = 'N/A', user_id: Optional[int] = None) -> Tuple[bool, str]:
        max_retries = 3
        last_error = "No response"

        for attempt in range(max_retries):
            start_time = time.time()
            key_id, key_value = self.resource_manager.get_key()
            
            if not key_value:
                return False, "No available API keys."

            try:
                model_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
                client = InferenceClient(model=model_url, token=key_value)
                
                # Try chat completion if possible
                try:
                    chat_response = client.chat_completion(
                        [{"role": "user", "content": prompt}],
                        max_tokens=1500,
                        temperature=0.7
                    )
                    content = chat_response.choices[0].message.content
                except:
                    # Fallback to text generation
                    content = client.text_generation(prompt, max_new_tokens=1024)

                if content:
                    duration = int((time.time() - start_time) * 1000)
                    self.resource_manager.log_usage(
                        model_name=self.model_name,
                        key_id=key_id,
                        feature=feature,
                        input_tokens=len(prompt)//4,
                        output_tokens=len(content)//4,
                        duration_ms=duration,
                        status='success',
                        context_ref=context_ref,
                        user_id=user_id
                    )
                    return True, content
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"HF API error: {e}")
                
                # Check for key issues
                if "401" in last_error or "Unauthorized" in last_error:
                    self.resource_manager.mark_key_exhausted(key_id)
                elif "429" in last_error:
                    self.resource_manager.force_refresh()
                    time.sleep(1)
                elif "503" in last_error or "loading" in last_error.lower():
                    time.sleep(5) # Wait for model load
                else:
                    break # Break on unknown errors
                    
        return False, f"HF failure: {last_error}"

    @staticmethod
    def get_available_models():
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            models = api.list_models(filter="text-generation", sort="downloads", direction=-1, limit=10)
            return [m.modelId for m in models]
        except:
            return []

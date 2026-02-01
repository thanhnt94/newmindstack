from typing import Optional, Union
from .schemas import AIRequestDTO, AIResponseDTO
from .services.ai_manager import get_ai_service

def generate_content(
    prompt: str, 
    feature: str = "general", 
    context_ref: Optional[str] = None
) -> AIResponseDTO:
    """
    Public API to generate content using the configured AI provider.
    
    Args:
        prompt: The text prompt to send.
        feature: The feature name for tracking (e.g. 'explanation', 'chat').
        context_ref: Optional reference string (e.g. 'Card #123') for logging.
        
    Returns:
        AIResponseDTO: Structured response with success status and content.
    """
    try:
        service = get_ai_service()
        if not service:
            return AIResponseDTO(
                success=False, 
                error="AI Service not configured or available."
            )
            
        success, result = service.generate_content(prompt, feature=feature, context_ref=context_ref)
        
        if success:
            return AIResponseDTO(success=True, content=result)
        else:
            return AIResponseDTO(success=False, error=result)
            
    except Exception as e:
        return AIResponseDTO(success=False, error=str(e))

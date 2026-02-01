from typing import Optional, Union
from .schemas import AIRequestDTO, AIResponseDTO
from .services.ai_manager import get_ai_service

def generate_content(
    prompt: str, 
    feature: str = "general", 
    context_ref: Optional[str] = None
) -> AIResponseDTO:
    """
    Core function to generate content.
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

class AIInterface:
    @staticmethod
    def generate_content(prompt: str, feature: str = "general", context_ref: Optional[str] = None) -> AIResponseDTO:
        """Core AI generation call."""
        return generate_content(prompt, feature, context_ref)

    @staticmethod
    def generate_item_explanation(item_id: int) -> str:
        """High-level helper to generate explanation for a specific learning item."""
        from mindstack_app.models import LearningItem, db
        from .logics.prompts import get_formatted_prompt
        
        item = LearningItem.query.get_or_404(item_id)
        prompt = get_formatted_prompt(item, purpose="explanation")
        if not prompt:
            raise ValueError("Could not format prompt for item.")
            
        result = AIInterface.generate_content(prompt, feature="explanation", context_ref=f"ITEM_{item_id}")
        if not result.success:
            raise RuntimeError(f"AI Generation Failed: {result.error}")
            
        item.ai_explanation = result.content
        db.session.commit()
        return result.content

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
    def generate_item_explanation(
        item_id: int, 
        user_id: Optional[int] = None, 
        custom_question: Optional[str] = None
    ) -> str:
        """High-level helper to generate explanation for a specific learning item."""
        from mindstack_app.models import LearningItem, db
        from .models import AiContent
        from .logics.prompts import get_formatted_prompt
        
        item = LearningItem.query.get_or_404(item_id)
        
        # Determine purpose and prompt
        purpose = "explanation"
        if custom_question:
            # If user asks a question, we incorporate it
            prompt = get_formatted_prompt(item, purpose="custom_question", custom_question=custom_question)
        else:
            prompt = get_formatted_prompt(item, purpose="explanation")
            
        if not prompt:
            raise ValueError("Could not format prompt for item.")
            
        result = AIInterface.generate_content(prompt, feature="explanation", context_ref=f"ITEM_{item_id}")
        if not result.success:
            raise RuntimeError(f"AI Generation Failed: {result.error}")
            
        # Get metadata
        meta = result.metadata or {}
        provider = meta.get('provider', 'gemini')
        model_name = meta.get('model_name', 'gemini-2.0-flash')

        # 1. Create AiContent record
        AiContent.query.filter_by(item_id=item_id, content_type='explanation').update({'is_primary': False})
        
        ai_content = AiContent(
            item_id=item_id,
            content_type='explanation',
            content_text=result.content,
            prompt=prompt,
            user_question=custom_question, 
            user_id=user_id,
            is_primary=True,
            provider=provider,
            model_name=model_name
        )
        db.session.add(ai_content)
        
        db.session.commit()
        return result.content

    @staticmethod
    def get_formatted_prompt(item, purpose="explanation", custom_question=None):
        """Get formatted prompt for an item."""
        from .logics.prompts import get_formatted_prompt
        return get_formatted_prompt(item, purpose=purpose, custom_question=custom_question)

    @staticmethod
    def get_default_request_interval():
        """Get default request interval constant."""
        from .services.explanation_service import DEFAULT_REQUEST_INTERVAL_SECONDS
        return DEFAULT_REQUEST_INTERVAL_SECONDS

    @staticmethod
    def generate_ai_explanations(task_id):
        """Wrapper to trigger background explanation generation."""
        from .services.explanation_service import generate_ai_explanations
        return generate_ai_explanations(task_id)

    @staticmethod
    def get_item_ai_contents(item_id: int, content_type: Optional[str] = None) -> list:
        """Get all AI generated contents for a specific item."""
        from .models import AiContent
        from mindstack_app.models import User, db
        
        query = db.session.query(AiContent, User.username).outerjoin(User, AiContent.user_id == User.user_id).filter(AiContent.item_id == item_id)
        
        if content_type:
            query = query.filter(AiContent.content_type == content_type)
        
        results = query.order_by(AiContent.created_at.desc()).all()
        return [
            {
                'content_id': ai_content.content_id,
                'content_text': ai_content.content_text,
                'content_type': ai_content.content_type,
                'user_question': ai_content.user_question,
                'username': username or 'Hệ thống', 
                'created_at': ai_content.created_at.isoformat(),
                'provider': ai_content.provider,
                'model_name': ai_content.model_name,
                'is_primary': ai_content.is_primary
            } for ai_content, username in results
        ]

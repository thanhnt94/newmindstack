"""
AI Gateway - Unified entry point for all AI interactions.
"""
from typing import Optional, Dict, Any, List

from flask import current_app

from ..service_manager import AIServiceManager
from ..logics.prompt_manager import PromptManager
from ..logics.response_parser import ResponseParser
from mindstack_app.core.signals import ai_token_used

class AIGateway:
    """
    Unified AI Service Gateway.
    
    Responsibilities:
    1. Manage Prompt Building (via PromptManager)
    2. Dispatch to Client (via AIServiceManager)
    3. Parse Response (via ResponseParser)
    4. Audit/Log Tokens (via Signals)
    """
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough estimation of tokens (char/4)."""
        if not text:
            return 0
        return len(text) // 4

    @staticmethod
    def generate_explanation(
        item_data: dict, 
        container_data: Optional[dict] = None,
        user_id: Optional[int] = None,
        custom_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate explanation for a learning item (Flashcard/Quiz).
        """
        # 1. Build Prompt
        prompt = PromptManager.build_explanation_prompt(
            item_data, container_data, custom_question
        )
        if not prompt:
            return {'success': False, 'message': 'Could not build prompt (missing data).'}
            
        # 2. Call Client
        client = AIServiceManager.get_service(current_app.app_context())
        
        # Get item info for logging (legacy)
        item_info = f"{item_data.get('item_type')}:{item_data.get('item_id')}"
        
        success, raw_result = client.generate_content(prompt, item_info=item_info)
        
        if not success:
            return {'success': False, 'message': raw_result}
            
        # 3. Parse Response
        clean_text = ResponseParser.clean_markdown(raw_result)
        
        # 4. Emit Signal (Audit)
        if user_id:
            input_tokens = AIGateway._estimate_tokens(prompt)
            output_tokens = AIGateway._estimate_tokens(clean_text)
            
            # Determine provider/model involved (best effort)
            # In hybrid client, it might be hard to know EXACTLY which one won without return
            # For now assume primary or just log 'hybrid'
            provider = getattr(client, 'primary_provider', 'unknown')
            model = 'auto' 
            
            ai_token_used.send(
                None,
                user_id=user_id,
                feature='explanation',
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_estimate=0.0 # TODO: implement cost calc
            )
            
        return {'success': True, 'content': clean_text, 'raw': raw_result}

    @staticmethod
    def chat(
        messages: List[Dict[str, str]], 
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simple chat interface suitable for ChatClient integration later.
        Using generate_content for now as clients don't expose chat_session yet.
        """
        # Simple concat prompt for now
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        prompt = f"Previous conversation:\n{conversation}\n\nAssistant:"
        
        client = AIServiceManager.get_service(current_app.app_context())
        success, raw_result = client.generate_content(prompt, item_info="chat_session")
        
        if success:
            clean_text = ResponseParser.clean_markdown(raw_result)
            return {'success': True, 'content': clean_text}
        
        return {'success': False, 'message': raw_result}

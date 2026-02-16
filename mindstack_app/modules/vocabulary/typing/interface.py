
from typing import List, Dict, Optional, Any
from .services.typing_service import TypingService

class VocabTypingInterface:
    """
    Public API for Vocab Typing Module.
    Follows Modular Monolith standards.
    """
    
    @staticmethod
    def get_available_content_keys(container_id: int) -> List[str]:
        """Get keys present in container content (excluding system keys)."""
        return TypingService.get_container_keys(container_id)

    @staticmethod
    def get_typing_eligible_items(container_id: int, user_id: int = None) -> List[Dict]:
        """Get items eligible for Typing generation."""
        return TypingService.get_eligible_items(container_id, user_id)

    @staticmethod
    def generate_typing_session_questions(container_id: int, config: Dict, user_id: int = None) -> List[Dict]:
        """Generate a list of questions for a Typing session."""
        return TypingService.generate_session_questions(container_id, config, user_id)

    @staticmethod
    def validate_typing_answer(user_input: str, correct_answer: str) -> Dict[str, Any]:
        """Validate typing answer."""
        return TypingService.check_result(user_input, correct_answer)

# Backward Compatibility Wrappers
def get_available_content_keys(container_id: int) -> List[str]:
    return VocabTypingInterface.get_available_content_keys(container_id)

def get_typing_eligible_items(container_id: int, user_id: int = None) -> List[Dict]:
    return VocabTypingInterface.get_typing_eligible_items(container_id, user_id)

def validate_typing_answer(user_input: str, correct_answer: str) -> Dict[str, Any]:
    return VocabTypingInterface.validate_typing_answer(user_input, correct_answer)

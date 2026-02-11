
from typing import List, Dict, Optional, Any
from .services.mcq_service import MCQService

class VocabMCQInterface:
    """
    Public API for Vocab MCQ Module.
    Follows Modular Monolith standards.
    """
    
    @staticmethod
    def get_available_content_keys(container_id: int) -> List[str]:
        """Get keys present in container content (excluding system keys)."""
        return MCQService.get_container_keys(container_id)

    @staticmethod
    def get_mcq_eligible_items(container_id: int, user_id: int = None) -> List[Dict]:
        """Get items eligible for MCQ generation."""
        return MCQService.get_eligible_items(container_id, user_id)

    @staticmethod
    def generate_mcq_session_questions(container_id: int, config: Dict, user_id: int = None) -> List[Dict]:
        """Generate a list of questions for an MCQ session."""
        return MCQService.generate_session_questions(container_id, config, user_id)

    @staticmethod
    def check_mcq_answer(correct_index: int, user_answer_index: int) -> Dict[str, Any]:
        """Check if selected answer is correct."""
        return MCQService.check_result(correct_index, user_answer_index)

# Backward Compatibility Wrappers
def get_available_content_keys(container_id: int) -> List[str]:
    return VocabMCQInterface.get_available_content_keys(container_id)

def get_mcq_eligible_items(container_id: int, user_id: int = None) -> List[Dict]:
    return VocabMCQInterface.get_mcq_eligible_items(container_id, user_id)

def generate_mcq_question(item: Dict, all_items: List[Dict], num_choices: int = 4, 
                          mode: str = 'front_back', question_key: str = None, 
                          answer_key: str = None, custom_pairs: List[Dict] = None) -> Dict:
    from .engine.mcq_engine import MCQEngine
    config = {
        'num_choices': num_choices,
        'mode': mode,
        'question_key': question_key,
        'answer_key': answer_key,
        'custom_pairs': custom_pairs
    }
    return MCQEngine.generate_question(item, all_items, config)

def check_mcq_answer(correct_index: int, user_answer_index: int) -> Dict[str, Any]:
    return VocabMCQInterface.check_mcq_answer(correct_index, user_answer_index)

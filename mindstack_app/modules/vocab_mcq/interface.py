
from typing import List, Dict, Optional, Any
from .logics import mcq_logic

def get_available_content_keys(container_id: int) -> List[str]:
    """
    Get keys present in container content (excluding system keys).
    """
    return mcq_logic.get_available_content_keys(container_id)

def get_mcq_eligible_items(container_id: int) -> List[Dict]:
    """
    Get items eligible for MCQ generation (with content merged).
    """
    return mcq_logic.get_mcq_eligible_items(container_id)

def generate_mcq_question(item: Dict, all_items: List[Dict], num_choices: int = 4, 
                          mode: str = 'front_back', question_key: str = None, 
                          answer_key: str = None, custom_pairs: List[Dict] = None) -> Dict:
    """
    Generate a single MCQ question for an item.
    """
    return mcq_logic.generate_mcq_question(
        item=item,
        all_items=all_items,
        num_choices=num_choices,
        mode=mode,
        question_key=question_key,
        answer_key=answer_key,
        custom_pairs=custom_pairs
    )

def check_mcq_answer(correct_index: int, user_answer_index: int) -> Dict[str, Any]:
    """
    Check if selected answer is correct and return result/score.
    """
    return mcq_logic.check_mcq_answer(correct_index, user_answer_index)

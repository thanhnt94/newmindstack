"""
Pure logic for MCQ generation - Algorithms and Pure Functions.
No Database access, no Models, no Flask.
"""

import random
from ..engine.selector import SmartDistractorSelector


def get_content_value(content: dict, key: str) -> str:
    """Helper to safely get content value as string."""
    val = content.get(key, '')
    if val is None:
        return ''
    if isinstance(val, list):
        return str(val[0]) if val else ''
    return str(val)


def select_smart_choices(correct_item: dict, distractor_pool: list, num_choices: int = 4) -> list:
    """
    Smart algorithm to select distractors based on similarity.
    
    Delegates to SmartDistractorSelector for intelligent distractor
    selection based on pre-filtering and morphological scoring.
    
    Args:
        correct_item: Dict {'text': str, 'front': str, 'back': str, 'item_id': int, ...}
        distractor_pool: List of dicts with 'text', 'front', 'back', 'item_id'.
        num_choices: Requested number of choices. If 0, dynamic [3, 4, 6].
        
    Returns:
        List of choices dicts including correct answer, shuffled.
    """
    # Dynamic Choice Count
    if not num_choices:
        num_choices = random.choices([3, 4, 6], weights=[1, 3, 1], k=1)[0]
        
    needed = num_choices - 1  # distractors needed (excluding correct answer)
    
    # --- Use SmartDistractorSelector for intelligent selection ---
    selected_items = SmartDistractorSelector.select(
        correct_item=correct_item,
        candidate_pool=distractor_pool,
        amount=needed
    )

    # Build final list
    choices_data = [correct_item] + selected_items
    random.shuffle(choices_data)
    
    return choices_data


# Alias for backward compatibility
select_choices = select_smart_choices

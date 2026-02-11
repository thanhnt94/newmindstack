"""
Pure logic for MCQ generation - Algorithms and Pure Functions.
No Database access, no Models, no Flask.
"""

import random

def get_content_value(content: dict, key: str) -> str:
    """Helper to safely get content value as string."""
    val = content.get(key, '')
    if val is None:
        return ''
    if isinstance(val, list):
        return str(val[0]) if val else ''
    return str(val)

def select_choices(correct_answer: str, distractor_pool: list, num_choices: int = 4) -> list:
    """
    Algorithm to select and shuffle distractors.
    
    Args:
        correct_answer: The correct answer text.
        distractor_pool: List of {'text': str, 'item_id': int} dicts.
        num_choices: Total number of choices. If 0, will pick randomly from [3, 4, 6].
        
    Returns:
        List of {'text': str, 'item_id': int} shuffled.
    """
    if not num_choices:
        num_choices = random.choice([3, 4, 6])
        
    # Remove duplicates from distractor pool (based on text)
    seen_texts = {correct_answer}
    unique_distractors = []
    for d in distractor_pool:
        if d['text'] not in seen_texts:
            unique_distractors.append(d)
            seen_texts.add(d['text'])
    
    # Select distractors
    num_distractors = min(num_choices - 1, len(unique_distractors))
    selected_distractors = random.sample(unique_distractors, num_distractors) if unique_distractors else []
    
    # Build choices and shuffle
    # We use -1 as a placeholder for the correct item_id if not provided, 
    # but service should pass the correct one.
    choices_data = [{'text': correct_answer}] + selected_distractors
    random.shuffle(choices_data)
    
    return choices_data

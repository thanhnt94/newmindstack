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
    selection based on length filtering and word/character overlap.
    
    Args:
        correct_item: Dict of correct item data {'text': str, 'item_id': int, 'type': str}.
        distractor_pool: List of distractor dicts with 'text', 'item_id', 'type'.
        num_choices: Requested number of choices. If 0, dynamic [3, 4, 6].
        
    Returns:
        List of choices dicts including correct answer, shuffled.
    """
    # Dynamic Choice Count
    if not num_choices:
        num_choices = random.choices([3, 4, 6], weights=[1, 3, 1], k=1)[0]
        
    correct_text = correct_item['text']
    needed = num_choices - 1  # distractors needed (excluding correct answer)
    
    # Filter duplicates
    seen = {correct_text}
    unique_pool = []
    for d in distractor_pool:
        if d['text'] not in seen:
            seen.add(d['text'])
            unique_pool.append(d)

    # --- Use SmartDistractorSelector for intelligent selection ---
    candidate_texts = [d['text'] for d in unique_pool]
    
    selected_texts = SmartDistractorSelector.select(
        correct_answer=correct_text,
        candidate_pool=candidate_texts,
        amount=needed
    )
    
    # Map selected texts back to their full dict (preserving item_id, type)
    text_to_item = {d['text']: d for d in unique_pool}
    selected_items = [text_to_item[t] for t in selected_texts if t in text_to_item]

    # Build final list
    choices_data = [{'text': correct_text, 'item_id': correct_item['item_id']}] + selected_items
    random.shuffle(choices_data)
    
    return choices_data


# Alias for backward compatibility
select_choices = select_smart_choices

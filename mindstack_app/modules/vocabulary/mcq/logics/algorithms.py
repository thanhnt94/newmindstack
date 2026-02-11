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

def select_smart_choices(correct_item: dict, distractor_pool: list, num_choices: int = 4) -> list:
    """
    Smart algorithm to select distractors based on similarity.
    
    Args:
        correct_item: Dict of correct item data {'text': str, 'item_id': int, 'type': str}.
        distractor_pool: List of distractor dicts.
        num_choices: Requested number of choices. If 0, dynamic [3, 4, 4, 4, 6].
        
    Returns:
        List of choices dicts including correct answer, shuffled.
    """
    # Dynamic Choice Count
    if not num_choices:
        num_choices = random.choices([3, 4, 6], weights=[1, 3, 1], k=1)[0]
        
    correct_text = correct_item['text']
    correct_type = correct_item.get('type', '')
    
    # Filter duplicates and self
    candidates = []
    seen = {correct_text}
    
    for d in distractor_pool:
        d_text = d['text']
        if d_text not in seen:
            seen.add(d_text)
            
            # Scoring Logic
            score = 0
            # 1. Startswith match (+2)
            if d_text and correct_text and d_text[0].lower() == correct_text[0].lower():
                score += 2
                
            # 2. Length similarity (+1)
            if abs(len(d_text) - len(correct_text)) <= 1:
                score += 1
                
            # 3. Type match (+1) - if available
            d_type = d.get('type', '')
            if correct_type and d_type and correct_type == d_type:
                score += 1
                
            candidates.append({'item': d, 'score': score})
            
    # Sort by score descending
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Select top N-1
    needed = num_choices - 1
    selected = [c['item'] for c in candidates[:needed]]
    
    # If not enough, fill with random remaining (already sorted, so just take next)
    # Actually candidates[:needed] already takes what's available. 
    # If we need more and candidates are exhausted, we can't do anything else.
    
    # Build final list
    choices_data = [{'text': correct_text, 'item_id': correct_item['item_id']}] + selected
    random.shuffle(choices_data)
    
    return choices_data

# Alias for backward compatibility if needed, but we will update caller
select_choices = select_smart_choices

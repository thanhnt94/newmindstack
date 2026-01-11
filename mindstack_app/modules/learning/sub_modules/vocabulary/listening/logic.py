# File: vocabulary/listening/logic.py
# Listening Learning Mode Logic

from mindstack_app.models import LearningItem, LearningProgress
from mindstack_app.utils.content_renderer import render_text_field
from datetime import datetime, timezone


def get_listening_eligible_items(container_id, mode='random', custom_pairs=None):
    """Get all items eligible for Listening mode from a container with mode filtering.
    With TTS, any item with text content is eligible (no audio URL required).
    """
    
    base_query = LearningItem.query.filter_by(
        container_id=container_id,
        item_type='FLASHCARD'
    )
    
    # Apply mode filtering
    if mode == 'new':
        # Items without any progress records
        base_query = base_query.filter(~LearningItem.progress_records.any())
    elif mode == 'review':
        # Items due for review
        now = datetime.now(timezone.utc)
        base_query = base_query.join(LearningProgress).filter(LearningProgress.due_time <= now)
    elif mode == 'hard':
        # Items with low easiness factor
        base_query = base_query.join(LearningProgress).filter(LearningProgress.easiness_factor < 2.5)
    elif mode == 'learned':
        # All items with progress
        base_query = base_query.join(LearningProgress)
    # 'random' = no filtering
    
    items = base_query.all()
    
    eligible = []
    for item in items:
        content = item.content or {}
        # With TTS, any item with front and back text is eligible
        if content.get('front') and content.get('back'):
            eligible.append({
                'item_id': item.item_id,
                'prompt': '???',
                'answer': content.get('front'),  # Keep original for validation
                'meaning': render_text_field(content.get('back')),  # BBCode rendering
                'content': content
            })
    
    return eligible


def check_listening_answer(correct_answer, user_answer):
    """Check if user's typed answer is close enough to correct."""
    correct = correct_answer.strip().lower()
    user = user_answer.strip().lower()
    
    # Exact match
    if correct == user:
        return {'correct': True, 'accuracy': 1.0}
    
    # Calculate similarity (simple Levenshtein distance-based)
    distance = levenshtein_distance(correct, user)
    max_len = max(len(correct), len(user), 1)
    similarity = 1 - (distance / max_len)
    
    # Accept if similarity > 0.8 (allow minor typos)
    if similarity >= 0.8:
        return {'correct': True, 'accuracy': similarity, 'typo': True}
    
    return {'correct': False, 'accuracy': similarity, 'correct_answer': correct_answer}


def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

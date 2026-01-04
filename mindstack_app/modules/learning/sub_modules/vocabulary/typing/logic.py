# File: vocabulary/typing/logic.py
# Typing Learning Mode Logic

from mindstack_app.models import LearningItem


def get_typing_eligible_items(container_id, custom_pairs=None, mode='random'):
    """Get all items eligible for Typing mode from a container."""
    from mindstack_app.models import LearningProgress, db
    from datetime import datetime, timezone

    base_query = LearningItem.query.filter_by(
        container_id=container_id,
        item_type='FLASHCARD'
    )
    
    # Filter by Mode
    if mode == 'new':
        # Items with NO progress
        # Use NOT EXISTS subquery
        items = base_query.filter(
            ~LearningItem.progress_records.any()
        ).all()
        
    elif mode == 'review':
        # Items due for review
        now = datetime.now(timezone.utc)
        items = base_query.join(LearningProgress).filter(
            LearningProgress.due_time <= now
        ).all()
        
    elif mode == 'learned':
        # All items with ANY progress
        items = base_query.join(LearningProgress).all()

    elif mode == 'hard':
        # Items with low stability or lapsing (simplified: easiness_factor < 2.5)
        items = base_query.join(LearningProgress).filter(
            LearningProgress.easiness_factor < 2.5
        ).all()
        
    else: # 'random' or 'custom'
        items = base_query.all()
    
    eligible = []
    
    # Logic for custom columns
    if custom_pairs and isinstance(custom_pairs, list):
        for item in items:
            # [UPDATED] Merge custom data into content
            content = dict(item.content or {})
            if item.custom_data:
                content.update(item.custom_data)
            
            # Find first valid pair in list
            valid_q = None
            valid_a = None
            
            for pair in custom_pairs:
                q_key = pair.get('q')
                a_key = pair.get('a')
                
                # Check directly in content (e.g. 'front', 'back', 'definition')
                if q_key in content and a_key in content:
                    valid_q = content[q_key]
                    valid_a = content[a_key]
                    break
            
            if valid_q and valid_a:
                 eligible.append({
                    'item_id': item.item_id,
                    'prompt': valid_q,
                    'answer': valid_a,
                    'audio_url': content.get('front_audio_url') if 'front' in [q_key, a_key] else None, 
                })
        return eligible

    # Default logic (Front -> Back)
    for item in items:
        content = item.content or {}
        # Need front and back for typing
        if content.get('front') and content.get('back'):
            eligible.append({
                'item_id': item.item_id,
                'prompt': content.get('front'),
                'answer': content.get('back'),
                'audio_url': content.get('front_audio_url'),
            })
    
    return eligible


def check_typing_answer(correct_answer, user_answer):
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

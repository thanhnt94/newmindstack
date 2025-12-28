# File: vocabulary/listening/logic.py
# Listening Learning Mode Logic

from mindstack_app.models import LearningItem


def get_listening_eligible_items(container_id):
    """Get all items eligible for Listening mode from a container."""
    items = LearningItem.query.filter_by(
        container_id=container_id,
        item_type='FLASHCARD'
    ).all()
    
    eligible = []
    for item in items:
        content = item.content or {}
        # Need back (answer) and audio for listening
        # Front text is optional for display after answering, but audio is MUST.
        if content.get('back') and (content.get('front_audio_url') or content.get('back_audio_url')):
            # Prefer front audio for question, but can support back? 
            # Usually Listening Dictation: Listen (Target Language) -> Write (Target Language) OR Listen (Target) -> Write (Native)?
            # Dictation usually means: Hear X -> Write X.
            # So if we have front_audio, answer is front text?
            # Or if we have back_audio, answer is back text?
            # Let's assume standard: Flashcard Front = Target Word. Back = Meaning.
            # Dictation: Hear Target Word (Front Audio) -> Type Target Word (Front Text).
            # So we check front audio and front text.
            
            if content.get('front') and content.get('front_audio_url'):
                eligible.append({
                    'item_id': item.item_id,
                    'prompt': '???', # Audio only
                    'answer': content.get('front'), # Type what you hear
                    'audio_url': content.get('front_audio_url'),
                    'meaning': content.get('back') # Show after answer
                })
            # What if only back audio exists? (e.g. Listen English -> Write English?)
            # Let's stick to Front=Target for now.
    
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

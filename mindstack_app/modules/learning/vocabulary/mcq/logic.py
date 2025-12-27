# File: vocabulary/mcq/logic.py
# MCQ (Multiple Choice Quiz) Logic for Vocabulary Learning

import random
from mindstack_app.models import LearningItem


def get_available_content_keys(container_id: int) -> list:
    """
    Scan items in the container to find available keys in the content JSON.
    Returns a list of keys that are present in at least one item, excluding system keys.
    """
    items = LearningItem.query.filter(
        LearningItem.container_id == container_id,
        LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
    ).all()
    
    keys = set()
    system_keys = {
        'audio_url', 'image_url', 'video_url', 
        'memrise_audio_url', 'front_audio_url', 'back_audio_url', 
        'front_img', 'back_img'
    }
    
    for item in items:
        content = item.content or {}
        for k in content.keys():
            if k not in system_keys:
                val = content[k]
                # Only include keys with string, int, or list values
                if isinstance(val, (str, int, float)) or (isinstance(val, list) and val):
                    keys.add(k)
    
    return sorted(list(keys))


def get_mcq_eligible_items(container_id: int) -> list:
    """
    Get items eligible for MCQ from a vocabulary container.
    Returns items with full content for custom column selection.
    """
    items = LearningItem.query.filter(
        LearningItem.container_id == container_id,
        LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
    ).all()
    
    eligible = []
    for item in items:
        content = item.content or {}
        # Include full content for custom key access
        eligible.append({
            'item_id': item.item_id,
            'content': content,
            'front': content.get('front', ''),
            'back': content.get('back', '')
        })
    
    return eligible


def get_mcq_mode_counts(user_id: int, container_id: int) -> dict:
    """
    Get learning statistics for MCQ setup page.
    Delegated to VocabularyStatsService for centralized stats logic.
    """
    from mindstack_app.modules.learning.vocabulary.stats import VocabularyStatsService
    return VocabularyStatsService.get_mode_counts(user_id, container_id)


def generate_mcq_question(item: dict, all_items: list, num_choices: int = 4, 
                          mode: str = 'front_back', question_key: str = None, 
                          answer_key: str = None, custom_pairs: list = None) -> dict:
    """
    Generate an MCQ question with distractors.
    
    Args:
        item: The target item (dict with item_id, content, front, back)
        all_items: All available items for distractor generation
        num_choices: Number of choices (including correct answer)
        mode: 'front_back', 'back_front', 'mixed', or 'custom'
        question_key: Custom key for question (when mode='custom')
        answer_key: Custom key for answer (when mode='custom')
        custom_pairs: List of {'q': question_key, 'a': answer_key} dicts for random selection
    
    Returns:
        Question dict with question text, choices, and correct answer index
    """
    content = item.get('content', {})
    current_mode = mode
    
    # Handle mixed mode - randomly pick direction
    if mode == 'mixed':
        current_mode = random.choice(['front_back', 'back_front'])
    
    # Handle custom pairs - randomly select one pair
    if mode == 'custom' and custom_pairs:
        pair = random.choice(custom_pairs)
        question_key = pair.get('q')
        answer_key = pair.get('a')
        current_mode = 'custom'
    
    # Determine question and answer based on mode
    if current_mode == 'custom' and question_key and answer_key:
        question_text = _get_content_value(content, question_key)
        correct_answer = _get_content_value(content, answer_key)
        # Build distractor pool from answer_key of other items
        distractor_pool = []
        for other in all_items:
            if other['item_id'] != item['item_id']:
                val = _get_content_value(other.get('content', {}), answer_key)
                if val and val != correct_answer:
                    distractor_pool.append(val)
    elif current_mode == 'back_front':
        question_text = item.get('back', '')
        correct_answer = item.get('front', '')
        distractor_pool = [i['front'] for i in all_items if i['item_id'] != item['item_id'] and i.get('front')]
    else:  # front_back (default)
        question_text = item.get('front', '')
        correct_answer = item.get('back', '')
        distractor_pool = [i['back'] for i in all_items if i['item_id'] != item['item_id'] and i.get('back')]
    
    # Remove duplicates from distractor pool
    distractor_pool = list(set([d for d in distractor_pool if d != correct_answer]))
    
    # Select distractors
    num_distractors = min(num_choices - 1, len(distractor_pool))
    distractors = random.sample(distractor_pool, num_distractors) if distractor_pool else []
    
    # Build choices and shuffle
    choices = [correct_answer] + distractors
    random.shuffle(choices)
    correct_index = choices.index(correct_answer) if correct_answer in choices else 0
    
    return {
        'item_id': item['item_id'],
        'question': question_text,
        'choices': choices,
        'correct_index': correct_index,
        'correct_answer': correct_answer,
        'question_key': question_key,
        'answer_key': answer_key
    }


def _get_content_value(content: dict, key: str) -> str:
    """Helper to safely get content value as string."""
    val = content.get(key, '')
    if isinstance(val, list):
        return val[0] if val else ''
    return str(val) if val else ''


def check_mcq_answer(correct_index: int, user_answer_index: int) -> dict:
    """
    Check if MCQ answer is correct.
    
    Returns:
        Result dict with is_correct, score, etc.
    """
    is_correct = correct_index == user_answer_index
    
    return {
        'is_correct': is_correct,
        'quality': 5 if is_correct else 0,  # For SRS: 5 = correct, 0 = wrong
        'score_change': 10 if is_correct else 0
    }

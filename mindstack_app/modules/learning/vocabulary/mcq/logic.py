# File: vocabulary/mcq/logic.py
# MCQ Learning Mode Logic

import random
from mindstack_app.models import LearningItem, db


def get_mcq_eligible_items(container_id):
    """Get all items eligible for MCQ from a container."""
    items = LearningItem.query.filter_by(
        container_id=container_id,
        item_type='FLASHCARD'
    ).all()
    
    eligible = []
    for item in items:
        content = item.content or {}
        # Check if has memrise data OR flashcard data
        if content.get('memrise_prompt') and content.get('memrise_answers'):
            eligible.append({
                'item_id': item.item_id,
                'prompt': content.get('memrise_prompt'),
                'answers': content.get('memrise_answers', []),
                'audio_url': content.get('memrise_audio_url'),
            })
        elif content.get('front') and content.get('back'):
            # Fallback to flashcard front/back
            eligible.append({
                'item_id': item.item_id,
                'prompt': content.get('front'),
                'answers': [content.get('back')],
                'audio_url': None,
            })
    
    return eligible


def generate_mcq_question(item, all_items, num_choices=4, mode='front_back'):
    """
    Generate an MCQ question with distractors.
    mode: 'front_back', 'back_front', 'mixed'
    """
    
    # Determine direction for this question
    current_mode = mode
    if mode == 'mixed':
        current_mode = random.choice(['front_back', 'back_front'])
    
    # Define primary prompt and answer based on mode
    # Default: Prompt = 'prompt' (Front), Answer = 'answers'[0] (Back)
    question_prompt = item['prompt']
    correct_answer = item['answers'][0] if item['answers'] else ''
    
    if current_mode == 'back_front':
        # Swap: Prompt = Back (Meaning), Answer = Front (Word)
        # Note: We need the reverse mapping. 
        # In `get_mcq_eligible_items`, 'prompt' is Front, 'answers' is Back.
        # So we swap them here.
        question_prompt = item['answers'][0] if item['answers'] else '???'
        correct_answer = item['prompt']
    
    # Get distractors from other items
    distractors = []
    other_items = [i for i in all_items if i['item_id'] != item['item_id']]
    random.shuffle(other_items)
    
    for other in other_items:
        # Determine distractor value based on mode
        distractor_val = ''
        if current_mode == 'front_back':
            # Distractors should be Backs (Meanings)
            distractor_val = other['answers'][0] if other['answers'] else ''
        else:
            # Distractors should be Fronts (Words)
            distractor_val = other['prompt']
            
        if distractor_val and distractor_val != correct_answer and distractor_val not in distractors:
            distractors.append(distractor_val)
            if len(distractors) >= num_choices - 1:
                break
    
    # Build choices
    choices = [correct_answer] + distractors
    random.shuffle(choices)
    
    return {
        'item_id': item['item_id'],
        'prompt': question_prompt,
        'audio_url': item['audio_url'] if current_mode == 'front_back' else None, # Only play audio if prompt is Front (Target Language)
        'choices': choices,
        'correct_answer': correct_answer,
        'correct_index': choices.index(correct_answer),
    }



from mindstack_app.modules.learning.srs.service import SrsService
from mindstack_app.modules.gamification.services import ScoreService
from mindstack_app.modules.shared.utils.db_session import safe_commit

def check_mcq_answer(item_id, user_answer, user_id=None):
    """
    Check if user's MCQ answer is correct.
    If user_id is provided, updates SRS progress and awards points.
    """
    item = LearningItem.query.get(item_id)
    if not item:
        return {'correct': False, 'message': 'Item not found'}
    
    content = item.content or {}
    correct_answers = content.get('memrise_answers', [])
    
    if not correct_answers:
        correct_answers = [content.get('back', '')]
    
    is_correct = user_answer.strip().lower() in [a.strip().lower() for a in correct_answers]
    
    # Update SRS and Score if user_id is present
    if user_id:
        # Determine rating: 4 (Good) if correct, 1 (Again) if incorrect
        quality = 4 if is_correct else 1
        
        # Update Progress
        SrsService.update_item_progress(user_id, item_id, quality, source_mode='mcq')
        
        # Award Points
        score_change = 0
        if is_correct:
            # TODO: Add config for MCQ scores? currently hardcoding
            score_change = 5
        
        ScoreService.award_points(
            user_id=user_id,
            amount=score_change,
            reason=f"MCQ Answer (Correct: {is_correct})",
            item_id=item_id,
            item_type='MCQ'
        )
        safe_commit(db.session)

    return {
        'correct': is_correct,
        'correct_answer': correct_answers[0] if correct_answers else '',
    }

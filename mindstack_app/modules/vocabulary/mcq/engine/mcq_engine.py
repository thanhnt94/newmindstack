"""
MCQ Business Rules Engine.
Pure logic, no Database access.
"""

import random
from ..logics.algorithms import get_content_value, select_choices
from mindstack_app.utils.bbcode_parser import bbcode_to_html

class MCQEngine:
    @staticmethod
    def generate_question(item_data: dict, all_items_data: list, config: dict) -> dict:
        """
        Generate a single MCQ question for an item based on configuration.
        """
        content = item_data.get('content', {})
        mode = config.get('mode', 'front_back')
        
        # 0. Handle Dynamic/Random Number of Choices
        num_choices_config = config.get('num_choices')
        if num_choices_config == 'random' or not isinstance(num_choices_config, int) or num_choices_config <= 0:
            # Weighted random: Favor 4 choices (60%), 3 (15%), 5 (15%), 6 (10%)
            num_choices = random.choices([3, 4, 5, 6], weights=[15, 60, 15, 10], k=1)[0]
        else:
            num_choices = num_choices_config

        question_key = config.get('question_key')
        answer_key = config.get('answer_key')
        custom_pairs = config.get('custom_pairs')
        
        # 1. Map mode to keys if not custom/specified
        if not question_key or not answer_key:
            if mode == 'back_front':
                question_key, answer_key = 'back', 'front'
            else:
                question_key, answer_key = 'front', 'back'

        # 2. Handle custom pairs (Randomize per question if multiple pairs)
        if custom_pairs:
            pair = random.choice(custom_pairs)
            question_key = pair.get('q')
            answer_key = pair.get('a')

        # 3. Handle mixed mode
        elif mode == 'mixed':
             if random.choice([True, False]):
                 question_key, answer_key = 'back', 'front'
             else:
                 question_key, answer_key = 'front', 'back'
        
        # 4. Extract Question and Correct Answer
        question_text = get_content_value(content, question_key)
        correct_answer = get_content_value(content, answer_key)
        
        # Determine which side is 'front' and 'back' for filtering logic
        # Usually front is the word and back is the meaning.
        item_front = get_content_value(content, 'front')
        item_back = get_content_value(content, 'back')

        # 5. Build Distractor Pool using BOTH sides for filtering
        distractor_pool = []
        
        # Shuffle a copy to ensure predictability is gone for tie-breaking
        shuffled_items = list(all_items_data)
        random.shuffle(shuffled_items)
        reveal_key = question_key
        for other in shuffled_items:
            if len(distractor_pool) >= 2000:
                break
                
            if other['item_id'] != item_data['item_id']:
                c = other.get('content', {})
                d_front = get_content_value(c, 'front')
                d_back = get_content_value(c, 'back')
                d_val = get_content_value(c, answer_key)
                
                d_reveal = get_content_value(c, reveal_key)
                if d_val:
                    distractor_pool.append({
                        'text': d_val, # The text to show in the choice
                        'reveal': d_reveal, # [NEW] Pre-calculated reveal text
                        'front': d_front,
                        'back': d_back,
                        'item_id': other['item_id'],
                        'type': c.get('type') or c.get('pos') or ''
                    })
            
        # 6. Select distractors using algorithms (pass dynamic num_choices)
        correct_item_data = {
            'text': correct_answer,
            'reveal': question_text, # [NEW] Reveal matches the question side
            'q_text': question_text, # [NEW] Pass question text for filtering
            'front': item_front,
            'back': item_back,
            'item_id': item_data['item_id'],
            'type': content.get('type') or content.get('pos') or ''
        }
        
        choices_data = select_choices(correct_item_data, distractor_pool, num_choices)
        
        choices = [c['text'] for c in choices_data]
        choice_item_ids = [c.get('item_id') for c in choices_data]
        
        # [NEW] Determine reveal text for each choice (the "question side")
        # Use the pre-calculated 'reveal' key from the choices
        choice_reveals = [c.get('reveal', '') for c in choices_data]
        
        correct_index = choices.index(correct_answer) if correct_answer in choices else 0
        
        # 7. Map Audio - Prioritize BACK/ANSWER audio for the question as requested
        a_audio_url = content.get(f"{answer_key}_audio") or content.get('back_audio') or content.get('back_audio_url')
        q_audio_url = a_audio_url or content.get(f"{question_key}_audio") or content.get('front_audio') or content.get('front_audio_url')

        # [NEW] Get media folders for BBCode resolution
        image_folder = config.get('image_folder')
        audio_folder = config.get('audio_folder')

        return {
            'item_id': item_data['item_id'],
            'question': bbcode_to_html(question_text, image_folder=image_folder, audio_folder=audio_folder),
            'choices': [bbcode_to_html(c, image_folder=image_folder, audio_folder=audio_folder) for c in choices],
            'choice_reveals': [bbcode_to_html(r, image_folder=image_folder, audio_folder=audio_folder) for r in choice_reveals],
            'choice_item_ids': choice_item_ids,
            'correct_index': correct_index,
            'correct_answer': bbcode_to_html(correct_answer, image_folder=image_folder, audio_folder=audio_folder),
            'question_key': question_key,
            'answer_key': answer_key,
            'question_audio': q_audio_url,
            'answer_audio': a_audio_url,
            'front_audio': content.get('front_audio') or content.get('front_audio_url'),
            'back_audio': content.get('back_audio') or content.get('back_audio_url'),
            'srs': item_data.get('srs')
        }

    @staticmethod
    def check_answer(correct_index: int, user_answer_index: int) -> dict:
        """
        Evaluate the user's answer (Pure Logic).
        Scoring is handled by the caller/manager.
        """
        return {
            'is_correct': correct_index == user_answer_index
        }

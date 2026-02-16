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
        num_choices = config.get('num_choices', 4)
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
        
        # 5. Build Distractor Pool using the same answer_key
        distractor_pool = []
        for other in all_items_data:
            if other['item_id'] != item_data['item_id']:
                c = other.get('content', {})
                val = get_content_value(c, answer_key)
                if val and val != correct_answer:
                    distractor_pool.append({
                        'text': val, 
                        'item_id': other['item_id'],
                        'type': c.get('type') or c.get('pos') or ''
                    })
            
        # 6. Select distractors using algorithms
        correct_item_data = {
            'text': correct_answer,
            'item_id': item_data['item_id'],
            'type': content.get('type') or content.get('pos') or ''
        }
        
        choices_data = select_choices(correct_item_data, distractor_pool, num_choices)
        
        choices = [c['text'] for c in choices_data]
        choice_item_ids = [c.get('item_id') for c in choices_data]
        correct_index = choices.index(correct_answer) if correct_answer in choices else 0
        
        # 7. Map Audio
        q_audio_url = content.get(f"{question_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
        a_audio_url = content.get(f"{answer_key}_audio") or content.get('front_audio') or content.get('front_audio_url')

        return {
            'item_id': item_data['item_id'],
            'question': bbcode_to_html(question_text),
            'choices': [bbcode_to_html(c) for c in choices],
            'choice_item_ids': choice_item_ids,
            'correct_index': correct_index,
            'correct_answer': bbcode_to_html(correct_answer),
            'question_key': question_key,
            'answer_key': answer_key,
            'question_audio': q_audio_url,
            'answer_audio': a_audio_url,
            'front_audio': content.get('front_audio') or content.get('front_audio_url'),
            'back_audio': content.get('back_audio') or content.get('back_audio_url')
        }

    @staticmethod
    def check_answer(correct_index: int, user_answer_index: int) -> dict:
        """Evaluate the user's answer."""
        is_correct = correct_index == user_answer_index
        return {
            'is_correct': is_correct,
            'quality': 5 if is_correct else 0,
            'score_change': 10 if is_correct else 0
        }

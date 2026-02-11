"""
MCQ Business Rules Engine.
Pure logic, no Database access.
"""

import random
from ..logics.algorithms import get_content_value, select_choices

class MCQEngine:
    @staticmethod
    def generate_question(item_data: dict, all_items_data: list, config: dict) -> dict:
        """
        Generate a single MCQ question for an item based on configuration.
        
        Args:
            item_data: Dict with 'item_id', 'content', 'front', 'back'.
            all_items_data: List of all items for distractors.
            config: Dict with 'mode', 'num_choices', 'question_key', 'answer_key', 'custom_pairs'.
        """
        content = item_data.get('content', {})
        mode = config.get('mode', 'front_back')
        num_choices = config.get('num_choices', 4)  # 0 means random 3,4,6
        question_key = config.get('question_key')
        answer_key = config.get('answer_key')
        custom_pairs = config.get('custom_pairs')
        
        current_mode = mode
        
        # Handle custom pairs
        if custom_pairs:
            pair = random.choice(custom_pairs)
            question_key = pair.get('q')
            answer_key = pair.get('a')
            current_mode = 'custom'
        elif mode == 'mixed':
            current_mode = random.choice(['front_back', 'back_front'])
        
        # Determine question and answer
        if current_mode == 'custom' and question_key and answer_key:
            question_text = get_content_value(content, question_key)
            correct_answer = get_content_value(content, answer_key)
            
            distractor_pool = []
            for other in all_items_data:
                if other['item_id'] != item_data['item_id']:
                    val = get_content_value(other.get('content', {}), answer_key)
                    if val and val != correct_answer:
                        distractor_pool.append({'text': val, 'item_id': other['item_id']})
        
        elif current_mode == 'back_front':
            question_text = item_data.get('back', '')
            correct_answer = item_data.get('front', '')
            distractor_pool = [
                {'text': i.get('front', ''), 'item_id': i['item_id']} 
                for i in all_items_data 
                if i['item_id'] != item_data['item_id'] and i.get('front')
            ]
        else:  # front_back (default)
            question_text = item_data.get('front', '')
            correct_answer = item_data.get('back', '')
            distractor_pool = [
                {'text': i.get('back', ''), 'item_id': i['item_id']} 
                for i in all_items_data 
                if i['item_id'] != item_data['item_id'] and i.get('back')
            ]
            
        # Select distractors using algorithms
        # Note: Correct item_id is handled in service or passed here
        choices_data = select_choices(correct_answer, distractor_pool, num_choices)
        
        # Patch the correct item_id back into the choices_data if it matches correct_answer
        for choice in choices_data:
            if choice['text'] == correct_answer:
                choice['item_id'] = item_data['item_id']
        
        choices = [c['text'] for c in choices_data]
        choice_item_ids = [c.get('item_id') for c in choices_data]
        correct_index = choices.index(correct_answer) if correct_answer in choices else 0
        
        return {
            'item_id': item_data['item_id'],
            'question': question_text,
            'choices': choices,
            'choice_item_ids': choice_item_ids,
            'correct_index': correct_index,
            'correct_answer': correct_answer,
            'question_key': question_key,
            'answer_key': answer_key
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

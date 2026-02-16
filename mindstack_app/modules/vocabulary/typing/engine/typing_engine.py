"""
Typing Business Rules Engine.
Pure logic, no Database access.
"""

import random
from ..logics.algorithms import get_content_value
from mindstack_app.utils.bbcode_parser import bbcode_to_html

class TypingEngine:
    @staticmethod
    def generate_question(item_data: dict, config: dict) -> dict:
        """
        Generate a single Typing question for an item based on configuration.
        """
        content = item_data.get('content', {})
        mode = config.get('mode', 'front_back')
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
        
        # 5. Map Audio
        q_audio_url = content.get(f"{question_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
        a_audio_url = content.get(f"{answer_key}_audio") or content.get('front_audio') or content.get('front_audio_url')

        return {
            'item_id': item_data['item_id'],
            'question': bbcode_to_html(question_text),
            'correct_answer': bbcode_to_html(correct_answer),
            'question_key': question_key,
            'answer_key': answer_key,
            'question_audio': q_audio_url,
            'answer_audio': a_audio_url,
            'front_audio': content.get('front_audio') or content.get('front_audio_url'),
            'back_audio': content.get('back_audio') or content.get('back_audio_url')
        }

    @staticmethod
    def validate_answer(user_input: str, correct_answer: str) -> dict:
        """
        Normalize both strings (lowercase, strip whitespace).
        Return True for exact matches.
        """
        if not user_input:
            user_input = ""
        if not correct_answer:
            correct_answer = ""

        # Remove HTML tags if any from correct_answer for comparison
        import re
        clean_answer = re.sub('<[^<]+?>', '', correct_answer)
        
        normalized_input = user_input.strip().lower()
        normalized_correct = clean_answer.strip().lower()
        
        is_correct = normalized_input == normalized_correct
        
        return {
            'is_correct': is_correct,
            'quality': 5 if is_correct else 0,
            'score_change': 15 if is_correct else 0 # Typing is harder, maybe more points?
        }

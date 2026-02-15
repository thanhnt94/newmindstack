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
                    c = other.get('content', {})
                    val = get_content_value(c, answer_key)
                    if val and val != correct_answer:
                        distractor_pool.append({
                            'text': val, 
                            'item_id': other['item_id'],
                            'type': c.get('type') or c.get('pos') or ''
                        })
        
        elif current_mode == 'back_front':
            question_text = item_data.get('back', '')
            correct_answer = item_data.get('front', '')
            distractor_pool = []
            for i in all_items_data:
                if i['item_id'] != item_data['item_id'] and i.get('front'):
                    c = i.get('content', {})
                    distractor_pool.append({
                        'text': i.get('front', ''),
                        'item_id': i['item_id'],
                        'type': c.get('type') or c.get('pos') or ''
                    })
        else:  # front_back (default)
            question_text = item_data.get('front', '')
            correct_answer = item_data.get('back', '')
            distractor_pool = []
            for i in all_items_data:
                if i['item_id'] != item_data['item_id'] and i.get('back'):
                    c = i.get('content', {})
                    distractor_pool.append({
                        'text': i.get('back', ''),
                        'item_id': i['item_id'],
                        'type': c.get('type') or c.get('pos') or ''
                    })
            
        # Select distractors using algorithms
        # Note: Correct item_id is handled in service or passed here
        
        # Prepare correct item data for scoring
        correct_item_data = {
            'text': correct_answer,
            'item_id': item_data['item_id'],
            'type': content.get('type') or content.get('pos') or '' # Try to find type/pos
        }
        
        # Pass full distractor pool to smart selector
        # We need to enrich distractor pool with type info for scoring if possible
        rich_distractor_pool = []
        for d in distractor_pool:
            rich_distractor_pool.append({
                'text': d['text'],
                'item_id': d['item_id'],
                'type': d.get('type') # Assuming passed distractor pool might have it, or we extract it
            })

        # Wait, constructed distractor_pool above only has text and item_id. 
        # We should update the construction logic above to include type/content if we want "type match" feature.
        # However, modifying the loops above is also needed.
        
        choices_data = select_choices(correct_item_data, distractor_pool, num_choices)
        
        # Smart selector returns full choice objects, no need to patch item_id manually 
        # unless it was missing (but select_smart_choices handles correct item inclusion)
        
        choices = [c['text'] for c in choices_data]
        choice_item_ids = [c.get('item_id') for c in choices_data]
        correct_index = choices.index(correct_answer) if correct_answer in choices else 0
        
        choices = [c['text'] for c in choices_data]
        choice_item_ids = [c.get('item_id') for c in choices_data]
        correct_index = choices.index(correct_answer) if correct_answer in choices else 0
        
        return {
            'item_id': item_data['item_id'],
            'question': bbcode_to_html(question_text),
            'choices': [bbcode_to_html(c) for c in choices],
            'choice_item_ids': choice_item_ids,
            'correct_index': correct_index,
            'correct_answer': bbcode_to_html(correct_answer),
            'question_key': question_key,
            'answer_key': answer_key,
            # [NEW] Audio Support - Always use front (target) audio for reinforcement
            'question_audio': item_data.get('content', {}).get('front_audio') or item_data.get('content', {}).get('front_audio_url'),
            'answer_audio': item_data.get('content', {}).get('front_audio') or item_data.get('content', {}).get('front_audio_url'),
            'front_audio': item_data.get('content', {}).get('front_audio') or item_data.get('content', {}).get('front_audio_url'),
            'back_audio': item_data.get('content', {}).get('back_audio') or item_data.get('content', {}).get('back_audio_url')
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

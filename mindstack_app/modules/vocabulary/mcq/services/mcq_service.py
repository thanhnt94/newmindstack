"""
MCQ Service - Orchestrates Database access and calls MCQ Engine.
"""

import random
from mindstack_app.models import LearningItem, db
from ..engine.mcq_engine import MCQEngine
from ..logics.algorithms import get_content_value

class MCQService:
    @staticmethod
    def get_container_keys(container_id: int) -> list:
        """Scan items in container to find available content keys."""
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        
        keys = set()
        system_keys = {
            'audio_url', 'image_url', 'video_url', 
            'memrise_audio_url', 'front_audio_url', 'back_audio_url', 
            'front_img', 'back_img', 'front_audio_content', 'back_audio_content'
        }
        
        for item in items:
            content = item.content or {}
            for k in content.keys():
                if k not in system_keys:
                    val = content[k]
                    if isinstance(val, (str, int, float)) or (isinstance(val, list) and val):
                        keys.add(k)
            
            custom = item.custom_data or {}
            for k in custom.keys():
                if k not in system_keys:
                    keys.add(k)
        
        return sorted(list(keys))

    @staticmethod
    def get_eligible_items(container_id: int, user_id: int = None) -> list:
        """
        Get processed items ready for MCQ engine.
        Filters for learned items (state != 0) if user_id is provided.
        """
        query = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )
        
        if user_id:
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            learned_ids = FSRSInterface.get_learned_item_ids_for_container(container_id, user_id)
            query = query.filter(LearningItem.item_id.in_(learned_ids))

        items = query.all()
        
        eligible = []
        for item in items:
            content = dict(item.content or {})
            if item.custom_data:
                content.update(item.custom_data)
                
            eligible.append({
                'item_id': item.item_id,
                'content': content,
                'front': content.get('front', ''),
                'back': content.get('back', '')
            })
        
        return eligible

    @staticmethod
    def get_all_items_for_distractors(container_id: int) -> list:
        """
        Get ALL items from container to be used as distractors pool.
        No user_id filtering (state agnostic).
        """
        return MCQService.get_eligible_items(container_id, user_id=None)

    @staticmethod
    def generate_session_questions(container_id: int, config: dict, user_id: int = None) -> list:
        """Orchestrate question generation for a session."""
        # 1. Load container settings for defaults
        from mindstack_app.models import LearningContainer
        container = LearningContainer.query.get(container_id)
        
        mcq_settings = (container.settings or {}).get('mcq', {}) if container else {}
        
        # Merge config with settings (config takes precedence)
        merged_config = {
            'mode': config.get('mode') or mcq_settings.get('mode', 'front_back'),
            'num_choices': config.get('num_choices') if config.get('num_choices') is not None else mcq_settings.get('choices', 0),
            'question_key': config.get('question_key') or mcq_settings.get('question_key'),
            'answer_key': config.get('answer_key') or mcq_settings.get('answer_key'),
            'custom_pairs': config.get('custom_pairs') or mcq_settings.get('pairs') or mcq_settings.get('custom_pairs'),
            'count': config.get('count') if config.get('count') is not None else mcq_settings.get('count', 10)
        }

        # 2. Get learned items (Questions Source) - ONLY items with state != 0
        eligible_questions = MCQService.get_eligible_items(container_id, user_id)
        if len(eligible_questions) < 1:
            return []
            
        # 3. Get all items (Distractors Source) - Whole container
        all_distractors = MCQService.get_all_items_for_distractors(container_id)
        
        # Ensure we have enough distractors in total (though engine handles graceful degradation)
        if len(all_distractors) < 2:
             return []

        random.shuffle(eligible_questions)
        
        count = merged_config.get('count', 10)
        if count > 0:
            selected_items = eligible_questions[:min(count, len(eligible_questions))]
        else:
            selected_items = eligible_questions
            
        questions = []
        for item in selected_items:
            # Pass ALL items as distractor pool
            question = MCQEngine.generate_question(item, all_distractors, merged_config)
            questions.append(question)
            
        return questions

    @staticmethod
    def check_result(correct_index: int, user_answer_index: int) -> dict:
        """Call engine to check answer."""
        return MCQEngine.check_answer(correct_index, user_answer_index)

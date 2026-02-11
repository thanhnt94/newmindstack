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
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        
        query = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )
        
        if user_id:
            query = query.join(
                ItemMemoryState, 
                ItemMemoryState.item_id == LearningItem.item_id
            ).filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.state != 0
            )

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

        # 2. Get learned items
        items = MCQService.get_eligible_items(container_id, user_id)
        if len(items) < 2:
            return []
            
        random.shuffle(items)
        
        count = merged_config.get('count', 10)
        if count > 0:
            selected_items = items[:min(count, len(items))]
        else:
            selected_items = items
            
        questions = []
        for item in selected_items:
            question = MCQEngine.generate_question(item, items, merged_config)
            questions.append(question)
            
        return questions

    @staticmethod
    def check_result(correct_index: int, user_answer_index: int) -> dict:
        """Call engine to check answer."""
        return MCQEngine.check_answer(correct_index, user_answer_index)

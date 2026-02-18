"""
MCQ Service - Orchestrates Database access and calls MCQ Engine.
"""

import random
from mindstack_app.models import LearningItem, db
from ..engine.mcq_engine import MCQEngine
from ..logics.algorithms import get_content_value
import asyncio
from flask import current_app
from mindstack_app.modules.audio.interface import AudioInterface

class MCQService:
    @staticmethod
    def ensure_audio_urls(item, container: 'LearningContainer' = None, q_key: str = None, a_key: str = None) -> dict:
        """
        Pre-generate audio if missing for specific content keys.
        Returns the content dict with resolved absolute URLs.
        """
        from flask import url_for
        
        # 1. Robustly extract item_id and content dict
        item_id = None
        content = None

        if hasattr(item, 'item_id'): # Model instance
            item_id = item.item_id
            content = dict(item.content or {})
        elif isinstance(item, dict):
            if 'content' in item and isinstance(item['content'], dict):
                item_id = item.get('item_id')
                content = dict(item.get('content') or {})
            else:
                # Direct content dict
                content = dict(item)

        if content is None:
            return {}

        # Prioritize provided keys, with fallbacks to front/back
        q_text = content.get(q_key) if q_key else content.get('front', '')
        a_text = content.get(a_key) if a_key else content.get('back', '')
        
        # Determine audio source texts (prefer audio-specific keys if they exist for the active fields)
        front_text = content.get('front_audio_content') or content.get('front', '')
        back_text = content.get('back_audio_content') or content.get('back', '')
        
        # Normalized existing URLs
        front_url = content.get('front_audio') or content.get('front_audio_url')
        back_url = content.get('back_audio') or content.get('back_audio_url')

        def _gen(text: str, filename: str, target_dir: str):
            if not text:
                return None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    AudioInterface.generate_audio(
                        text=str(text), 
                        auto_voice_parsing=True,
                        custom_filename=filename,
                        target_dir=target_dir
                    )
                )
                loop.close()
                return result.url if result and result.status in ('generated', 'exists') else None
            except Exception as e:
                current_app.logger.warning(f"Failed to generate audio in MCQ: {e}")
                return None

        # Determine target directory and convention
        audio_folder = "uploads/audio/cache"
        if container:
            from mindstack_app.utils.media_paths import normalize_media_folder
            container_audio = (container.settings or {}).get('media_folders', {}).get('audio') or container.media_audio_folder
            if container_audio:
                audio_folder = f"uploads/{normalize_media_folder(container_audio)}"

        def _resolve_abs_url(val, folder):
            """Ensure URL is absolute starting with /media/ or external prefix."""
            if not val:
                return val
            
            val_str = str(val)
            if val_str.startswith(('http://', 'https://', '/')):
                return val_str
                
            from mindstack_app.utils.media_paths import build_relative_media_path
            rel = build_relative_media_path(val, folder.replace('uploads/', '') if folder.startswith('uploads/') else folder)
            if rel:
                try:
                    return url_for('media_uploads', filename=rel.lstrip('/'), _external=False)
                except:
                    return f"/media/{rel.lstrip('/')}"
            return val_str

        # Normalize existing URLs
        if front_url:
            front_url = _resolve_abs_url(front_url, audio_folder)
            content['front_audio'] = front_url
            content['front_audio_url'] = front_url
            
        if back_url:
            back_url = _resolve_abs_url(back_url, audio_folder)
            content['back_audio'] = back_url
            content['back_audio_url'] = back_url

        # Check for Custom Keys Audio Generation
        # (Assuming custom key `k` might have `k_audio` key)
        for key in [q_key, a_key]:
            if key and key not in ('front', 'back'):
                audio_key = f"{key}_audio"
                if not content.get(audio_key) and content.get(key):
                    filename = f"{key}_{item_id}.mp3" if item_id else None
                    url = _gen(content.get(key), filename, audio_folder)
                    if url:
                        content[audio_key] = url

        # Fallback to standard front/back generation
        if front_text and not front_url and str(front_text).strip():
            filename = f"front_{item_id}.mp3" if item_id else None
            url = _gen(front_text, filename, audio_folder)
            if url:
                content['front_audio'] = url
                content['front_audio_url'] = url
            
        if back_text and not back_url and str(back_text).strip():
            filename = f"back_{item_id}.mp3" if item_id else None
            url = _gen(back_text, filename, audio_folder)
            if url:
                content['back_audio'] = url
                content['back_audio_url'] = url

        return content

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
                if k not in system_keys and not k.endswith('_audio'):
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
                'content': content
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
            'count': config.get('count') if config.get('count') is not None else mcq_settings.get('count', 0)
        }

        # 2. Get learned items (Questions Source)
        study_mode = config.get('study_mode', 'review')
        if study_mode == 'random':
            eligible_questions = MCQService.get_eligible_items(container_id, user_id=None)
        else:
            eligible_questions = MCQService.get_eligible_items(container_id, user_id)
            
        if len(eligible_questions) < 1:
            return []
            
        # 3. Get all items (Distractors Source) - Whole container
        all_distractors = MCQService.get_all_items_for_distractors(container_id)
        
        # Ensure we have enough distractors in total (though engine handles graceful degradation)
        if len(all_distractors) < 2:
             return []

        random.shuffle(eligible_questions)
        
        count = merged_config.get('count', 0)
        if count > 0:
            selected_items = eligible_questions[:min(count, len(eligible_questions))]
        else:
            selected_items = eligible_questions
            
        questions = []
        for item in selected_items:
            # Ensure audio URLs are present with context - CAPTURE RETURN
            updated_content = MCQService.ensure_audio_urls(
                item, 
                container, 
                q_key=merged_config['question_key'], 
                a_key=merged_config['answer_key']
            )
            
            # Update item content before passing to engine
            if isinstance(item, dict):
                item['content'] = updated_content
            
            # Pass ALL items as distractor pool
            question = MCQEngine.generate_question(item, all_distractors, merged_config)
            questions.append(question)
            
        return questions

    @staticmethod
    def check_result(correct_index: int, user_answer_index: int, config: dict = None) -> dict:
        """Call engine to check answer."""
        return MCQEngine.check_answer(correct_index, user_answer_index, config)

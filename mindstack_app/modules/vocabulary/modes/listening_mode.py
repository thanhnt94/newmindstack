"""
Listening Mode
==============
Listening practice mode using the Session Driver architecture.
Focuses on audio-first verification.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time

from .base_mode import BaseVocabMode, EvaluationResult

class ListeningMode(BaseVocabMode):
    """
    Listening Mode.
    
    - **Format**: 
        - Audio URL (primary)
        - Hint (optional, text/front)
        - Answer Length (hidden hint)
    - **Interaction**: User listens and types the answer.
    - **Scoring**: String comparison (case-insensitive).
    """

    def get_mode_id(self) -> str:
        return 'listening'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # [NEW] Get media folders from container for path resolution
        from mindstack_app.models import LearningContainer
        from mindstack_app.utils.media_paths import resolve_media_in_content
        from mindstack_app.utils.bbcode_parser import bbcode_to_html
        
        container_id = item.get('container_id')
        container = LearningContainer.query.get(container_id) if container_id else None
        audio_folder = container.media_audio_folder if container else None
        image_folder = container.media_image_folder if container else None
        
        # Resolve dedicated fields in a copy of content
        resolved_content = resolve_media_in_content(dict(content), audio_folder=audio_folder, image_folder=image_folder)
        
        # Determine Audio Source
        audio_url = resolved_content.get('front_audio_url') or resolved_content.get('back_audio_url')
        
        # Text for fallback TTS or display
        audio_text = content.get('front') or content.get('term') or ''
        answer_text = content.get('back') or content.get('definition') or content.get('answer') or ''
        
        # Render BBCode for hint
        raw_hint = content.get('hint') or content.get('front') or ''
        rendered_hint = bbcode_to_html(raw_hint, audio_folder=audio_folder, image_folder=image_folder)
        
        return {
            'type': 'listening',
            'item_id': item.get('item_id'),
            'audio_url': audio_url,
            'audio_text': audio_text, 
            'hint': rendered_hint,
            'answer_length': len(answer_text) if answer_text else 0,
            'meta': {
                'settings': settings or {}
            }
        }
    
    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate Listening answer.
        """
        from mindstack_app.modules.scoring.interface import ScoringInterface
        from mindstack_app.models import LearningContainer
        from mindstack_app.utils.media_paths import resolve_media_in_content
        
        container_id = item.get('container_id')
        container = LearningContainer.query.get(container_id) if container_id else None
        
        content = item.get('content', {}) or {}
        # Resolve paths for feedback as well
        resolved_content = resolve_media_in_content(dict(content), 
                                                   audio_folder=container.media_audio_folder if container else None,
                                                   image_folder=container.media_image_folder if container else None)
        
        correct_answer = (content.get('back') or content.get('definition') or content.get('answer') or '').strip()
        user_text = (user_input.get('text') or '').strip()

        # Simple Normalization
        is_correct = user_text.lower() == correct_answer.lower()
        
        if is_correct:
            score_change = ScoringInterface.get_score_value('VOCAB_LISTENING_CORRECT_BONUS')
            quality = 4  # Easy/Perfect
        else:
            score_change = 0
            quality = 1  # Again
            
        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=score_change,
            feedback={
                'correct_answer': correct_answer,
                'user_text': user_text,
                'audio_url': resolved_content.get('front_audio_url') or resolved_content.get('back_audio_url') 
            }
        )

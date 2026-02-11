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
        """
        Generate Listening Interaction.
        """
        content = item.get('content', {}) or {}
        
        # Determine Audio Source
        # Prefer 'front' audio if available, else 'back'
        audio_url = content.get('front_audio_url') or content.get('back_audio_url')
        
        # If no explicit URL, maybe we can use TTS on the front text?
        # For now, follow legacy logic: rely on stored URLs.
        # Fallback: if no URL, client might use TTS if text is provided in 'audio_text'
        audio_text = content.get('front') or content.get('term') or ''
        
        answer_text = content.get('back') or content.get('definition') or content.get('answer') or ''
        
        return {
            'type': 'listening',
            'item_id': item.get('item_id'),
            'audio_url': audio_url,
            'audio_text': audio_text, # For fallback TTS on client
            'hint': content.get('hint') or content.get('front') or '', # Optional text hint
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
        Input: `{'text': str}`
        """
        content = item.get('content', {}) or {}
        correct_answer = (content.get('back') or content.get('definition') or content.get('answer') or '').strip()
        user_text = (user_input.get('text') or '').strip()

        # Simple Normalization
        is_correct = user_text.lower() == correct_answer.lower()
        
        score_change = 0
        quality = 0
        
        if is_correct:
            score_change = 10
            quality = 5 # Perfect
        else:
            # Maybe check for "close enough" (typos)?
            # For now, strict strict equality for 100% match
            quality = 1 # Wrong
            
        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=score_change,
            feedback={
                'correct_answer': correct_answer,
                'user_text': user_text,
                'audio_url': content.get('front_audio_url') or content.get('back_audio_url') 
            }
        )

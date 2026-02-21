"""
Typing Mode
===========
Typing practice mode using the Session Driver architecture.
Requires user to type the exact answer (case-insensitive).
"""

import random
from typing import Any, Dict, Optional, List
from dataclasses import dataclass

from .base_mode import BaseVocabMode, EvaluationResult

class TypingMode(BaseVocabMode):
    """
    Typing Practice Mode.
    
    - **Format**: prompt (front), hint (scrambled back), length.
    - **Evaluate**: Strict string comparison (case-insensitive).
    """

    def get_mode_id(self) -> str:
        return 'typing'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Typing interaction.
        """
        # Data Extraction (Robust)
        content = item.get('content', {}) or {}
        
        # Determine Prompt/Answer based on direction
        # Default: Prompt = Front, Answer = Back
        direction = settings.get('direction', 'front_back') if settings else 'front_back'
        
        front = content.get('front') or content.get('term') or content.get('question') or ''
        back = content.get('back') or content.get('definition') or content.get('answer') or content.get('explanation') or ''
        
        if direction == 'back_front':
            prompt_text = back
            target_text = front
        else:
            prompt_text = front
            target_text = back

        # 2. BBCode Rendering & Path Resolution for Prompt
        from mindstack_app.utils.bbcode_parser import bbcode_to_html
        from mindstack_app.models import LearningContainer
        
        container_id = item.get('container_id')
        container = LearningContainer.query.get(container_id) if container_id else None
        audio_folder = container.media_audio_folder if container else None
        image_folder = container.media_image_folder if container else None
        
        rendered_prompt = bbcode_to_html(prompt_text, audio_folder=audio_folder, image_folder=image_folder)

        # 3. Generate Scrambled Hint (from raw text, not rendered)
        hint_text = self._scramble_text(target_text)
        
        return {
            'type': 'typing',
            'item_id': item.get('item_id'),
            'question': rendered_prompt,
            'hint': hint_text,
            'length': len(target_text),
            'meta': {
                'direction': direction
            }
        }

    def _scramble_text(self, text: str) -> str:
        """Simple scrambler that keeps first/last char if long enough."""
        if not text:
            return ""
        
        words = text.split()
        scrambled_words = []
        
        for word in words:
            if len(word) <= 3:
                scrambled_words.append(word)
                continue
            
            middle = list(word[1:-1])
            random.shuffle(middle)
            scrambled_words.append(word[0] + "".join(middle) + word[-1])
            
        return " ".join(scrambled_words)

    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate Typing answer.
        """
        from mindstack_app.modules.scoring.interface import ScoringInterface
        
        # Extract correct answer again (stateless)
        content = item.get('content', {}) or {}
        direction = settings.get('direction', 'front_back') if settings else 'front_back'
        
        front = content.get('front') or content.get('term') or content.get('question') or ''
        back = content.get('back') or content.get('definition') or content.get('answer') or content.get('explanation') or ''
        
        if direction == 'back_front':
            correct_text = front
        else:
            correct_text = back
            
        # Normalize
        user_text = (user_input.get('text') or '').strip().lower()
        correct_text = str(correct_text).strip().lower()
        
        is_correct = (user_text == correct_text)
        
        # Scoring
        if is_correct:
            score_change = ScoringInterface.get_score_value('VOCAB_TYPING_CORRECT_BONUS')
            quality = 4  # Easy (Typed correctly)
        else:
            score_change = 0
            quality = 1  # Again

        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=score_change,
            feedback={
                'correct_answer': item.get('content', {}).get('back', ''), 
                'display_answer': correct_text if direction == 'back_front' else back,
                'user_text': user_input.get('text'),
            }
        )

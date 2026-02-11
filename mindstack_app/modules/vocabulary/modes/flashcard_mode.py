# File: mindstack_app/modules/vocabulary/modes/flashcard_mode.py
"""
Flashcard Mode
==============
Classic two-sided flashcard mode with self-assessed quality rating.

The learner sees the *front* of the card, mentally recalls the
answer, flips to reveal the *back*, then self-rates (Again / Hard /
Good / Easy → quality 1-4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_mode import BaseVocabMode, EvaluationResult


class FlashcardMode(BaseVocabMode):
    """
    Flashcard (self-rated) mode.

    ``format_interaction`` simply exposes front / back / content.
    ``evaluate_submission`` trusts the learner's quality rating.
    """

    # Score mapping: quality → gamification points
    _SCORE_MAP: Dict[int, int] = {
        1: 0,    # Again  → no points
        2: 5,    # Hard   → partial
        3: 10,   # Good   → standard
        4: 15,   # Easy   → bonus
    }

    def get_mode_id(self) -> str:
        return 'flashcard'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build a flashcard payload with full frontend support (BBCode, Stats, Audio).
        """
        # 1. BBCode Rendering
        from mindstack_app.utils.content_renderer import render_content_dict
        raw_content = item.get('content', {})
        rendered_content = render_content_dict(raw_content)

        # 2. Media Path Resolution (Audio/Images)
        from mindstack_app.utils.media_paths import build_relative_media_path
        from mindstack_app.models import LearningContainer
        
        container_id = item.get('container_id')
        container = LearningContainer.query.get(container_id) if container_id else None
        media_folder = container.media_audio_folder if container else None
        
        # Resolve audio paths in rendered content
        for field in ['front_audio_url', 'back_audio_url', 'front_img', 'back_img']:
            val = rendered_content.get(field)
            if val and not val.startswith(('http://', 'https://', '/')):
                rel_path = build_relative_media_path(val, media_folder)
                if rel_path:
                    rendered_content[field] = f"/media/{rel_path}"

        # 3. Fetch Stats (Local import to avoid cycle with core -> vocab_mode -> core)
        from mindstack_app.modules.vocabulary.flashcard.engine.core import FlashcardEngine
        from flask_login import current_user
        
        # Assuming current_user is available in context (it usually is for web requests)
        initial_stats = {}
        if current_user and current_user.is_authenticated:
            initial_stats = FlashcardEngine.get_item_statistics(current_user.user_id, item.get('item_id'))

        # 4. Construct Final Payload
        return {
            'type': 'flashcard',
            'item_id': item.get('item_id'),
            'container_id': container_id,
            'container_title': container.title if container else '',
            'front': rendered_content.get('front', ''),
            'back': rendered_content.get('back', ''),
            'content': rendered_content, # Includes resolved media URLs
            'initial_stats': initial_stats,
            'ai_explanation': item.get('ai_explanation', ''),
            # Helpers for frontend logic
            'can_edit': (container.creator_user_id == current_user.user_id) if container and current_user.is_authenticated else False,
        }

    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Accept the learner's self-rated quality.

        Expected ``user_input`` shape::

            {"quality": 3}          # 1=Again, 2=Hard, 3=Good, 4=Easy

        Quality 1 is considered *incorrect* for statistics purposes;
        qualities 2-4 are considered *correct*.
        """
        quality = user_input.get('quality', 3)
        quality = max(1, min(4, quality))       # clamp to 1-4

        is_correct = quality >= 2
        score = self._SCORE_MAP.get(quality, 0)

        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=score,
            feedback={'rated_quality': quality},
        )

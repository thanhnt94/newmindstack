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
import flask

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
            try:
                initial_stats = FlashcardEngine.get_item_statistics(current_user.user_id, item.get('item_id'))
                # Remove streak as requested
                if 'current_streak' in initial_stats:
                    del initial_stats['current_streak']
            except Exception as e:
                pass # Silent fail in production
        else:
            pass

        # 4. Backend Rendering [Refactor - Thin Client]
        from ..flashcard.engine.renderer import FlashcardRenderer
        
        display_settings = {
            'can_edit': (container.creator_user_id == current_user.user_id) if container and current_user.is_authenticated else False,
            'edit_url': flask.url_for('content_management.edit_item', container_id=container_id, item_id=item.get('item_id')) if container else '',
            'is_media_hidden': settings.get('hide_media', False),
            'is_audio_autoplay': settings.get('autoplay', True)
        }
        
        # Merge theme-specific display settings from config
        from ..flashcard.interface import FlashcardInterface
        flash_config = FlashcardInterface.get_all_configs()
        display_settings.update(flash_config.get('displaySettings', {}))
        
        # We need to bridge some fields for the renderer
        item_for_renderer = {
            'id': item.get('item_id'),
            'front_text': rendered_content.get('front', ''),
            'back_text': rendered_content.get('back', ''),
            'front_image': rendered_content.get('front_img'),
            'back_image': rendered_content.get('back_img'),
            'front_audio_url': rendered_content.get('front_audio_url'),
            'back_audio_url': rendered_content.get('back_audio_url'),
            'has_front_audio': bool(rendered_content.get('front_audio_url')),
            'has_back_audio': bool(rendered_content.get('back_audio_url')),
            'front_audio_content': rendered_content.get('front_audio_content') or rendered_content.get('front', ''),
            'back_audio_content': rendered_content.get('back_audio_content') or rendered_content.get('back', ''),
            'category': rendered_content.get('category', 'default'),
            'buttons_html': rendered_content.get('buttons_html', '') # This might come from elsewhere
        }
        
        html_payload = FlashcardRenderer.render_item(item_for_renderer, initial_stats, display_settings=display_settings)

        # 5. Construct Final Payload
        return {
            'type': 'flashcard',
            'item_id': item.get('item_id'),
            'container_id': container_id,
            'container_title': container.title if container else '',
            'front': rendered_content.get('front', ''),
            'back': rendered_content.get('back', ''),
            'html_front': html_payload['front'],
            'html_back': html_payload['back'],
            'html_full': html_payload['full_html'],
            'content': rendered_content, # Includes resolved media URLs
            'initial_stats': initial_stats,
            'ai_explanation': item.get('ai_explanation', ''),
            # Helpers for frontend logic
            'can_edit': display_settings['can_edit'],
            'edit_url': display_settings['edit_url'],
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
        """
        from mindstack_app.modules.scoring.interface import ScoringInterface
        
        quality = user_input.get('quality', 3)
        quality = max(1, min(4, quality))       # clamp to 1-4

        is_correct = quality >= 2
        
        # [NEW] Map quality to config keys
        config_keys = {
            1: 'SCORE_FSRS_AGAIN',
            2: 'SCORE_FSRS_HARD',
            3: 'SCORE_FSRS_GOOD',
            4: 'SCORE_FSRS_EASY'
        }
        event_key = config_keys.get(quality, 'SCORE_FSRS_GOOD')
        
        # Gather Context for Deep Scoring
        # 1. Difficulty (Pre-review)
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        # Try to get user_id from settings, fallback to current_user
        user_id = settings.get('user_id')
        if not user_id:
            try:
                from flask_login import current_user
                if current_user and current_user.is_authenticated:
                    user_id = current_user.user_id
            except ImportError:
                pass
                
        difficulty = 0.0
        streak = 0
        
        if user_id:
            # Fetch Pre-state for difficulty bonus
            # We use a direct query to avoid heavyweight service overhead here, 
            # or use FSRSInterface if preferred.
            pre_state = ItemMemoryState.query.filter_by(
                user_id=user_id, 
                item_id=item.get('item_id')
            ).first()
            if pre_state:
                difficulty = pre_state.difficulty
                
            # Fetch Streak
            try:
                from mindstack_app.modules.gamification.services.scoring_service import ScoreService
                streak = ScoreService.calculate_current_streak(user_id)
            except ImportError:
                pass

        context = {
            'difficulty': difficulty,
            'streak': streak,
            'duration_ms': user_input.get('duration_ms', 0)
        }

        total_score, breakdown = ScoringInterface.calculate_breakdown(event_key, context)
        
        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=total_score,
            breakdown=breakdown,
            feedback={'rated_quality': quality},
        )

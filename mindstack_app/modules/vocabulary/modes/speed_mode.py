"""
Speed Mode
==========
Speed Test mode using the Session Driver architecture.
Extends MCQ logic with time constraints and speed bonuses.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time

from .base_mode import BaseVocabMode, EvaluationResult
from mindstack_app.modules.vocabulary.mcq.engine.mcq_engine import MCQEngine
from mindstack_app.models import LearningItem

class SpeedMode(BaseVocabMode):
    """
    Speed Mode (Rapid Fire MCQ).
    
    - **Format**: Similar to MCQ (1 question + 3 distractors).
    - **Time Limit**: Enforced via metadata (frontend countdown).
    - **Scoring**: Base points + Speed Bonus (if answered quickly).
    """

    def get_mode_id(self) -> str:
        return 'speed'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Speed Question.
        Reuses `MCQEngine` for question generation.
        Adds timeout metadata.
        """
        # Fallback: Fetch distractors if pool is small
        pool = all_items or []
        if len(pool) < 4:
            pool = self._fetch_distractors(item.get('container_id'), limit=10)

        # Default config
        settings = settings or {}
        timeout_ms = settings.get('timeout_ms', 5000) # Default 5s
        
        config = {
            'mode': settings.get('direction', 'front_back'),
            'num_choices': 4, # Fixed to 4 for consistency
            'question_key': settings.get('question_key'),
            'answer_key': settings.get('answer_key'),
            'custom_pairs': settings.get('custom_pairs'),
        }

        # Adapter: Flatten content
        prepared_item = self._flatten_content(item)
        prepared_pool = [self._flatten_content(i) for i in pool]

        # Generate via Engine
        engine_result = MCQEngine.generate_question(prepared_item, prepared_pool, config)

        return {
            'type': 'speed',
            'item_id': item.get('item_id'),
            'question': engine_result.get('question'),
            'options': engine_result.get('choices'),
            'option_ids': engine_result.get('choice_item_ids'),
            'correct_id': item.get('item_id'), # (Optional)
            'correct_index': engine_result.get('correct_index'),
            'meta': {
                'direction': config['mode'],
                'settings': {
                    'timeout_ms': timeout_ms
                }
            }
        }

    def _flatten_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to ensure 'front'/'back' exist at top level."""
        flat = item.copy()
        content = item.get('content', {}) or {}
        
        if 'front' not in flat:
            flat['front'] = content.get('front') or content.get('term') or content.get('question') or ''
        if 'back' not in flat:
            flat['back'] = content.get('back') or content.get('definition') or content.get('answer') or content.get('explanation') or ''
            
        return flat

    def _fetch_distractors(self, container_id: Optional[int], limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch random items from the same container."""
        if not container_id:
            return []
        try:
            from sqlalchemy.sql.expression import func
            items = LearningItem.query.filter(
                LearningItem.container_id == container_id,
                LearningItem.is_deleted == False
            ).order_by(func.random()).limit(limit).all()
            
            return [
                {
                    'item_id': i.item_id,
                    'content': i.content
                }
                for i in items
            ]
        except Exception:
            return []

    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate Speed answer.
        Input: `{'selected_option_id': int, 'duration_ms': int}`
        """
        correct_id = item.get('item_id')
        selected_id = user_input.get('selected_option_id')
        duration_ms = user_input.get('duration_ms', 5000)

        # Check Correctness (Stateless ID check)
        is_correct = False
        if selected_id is not None:
            try:
                is_correct = (int(selected_id) == int(correct_id))
            except (ValueError, TypeError):
                is_correct = False
        
        # Scoring Logic
        score_change = 0
        quality = 1 # Default Again

        if is_correct:
            base_points = 10
            bonus = 0
            
            # Speed Bonus: < 1.5s = +5, < 3s = +2
            if duration_ms < 1500:
                bonus = 5
            elif duration_ms < 3000:
                bonus = 2
            
            score_change = base_points + bonus
            quality = 3 # Good (Standard pass)
            
            # If extremely fast, maybe Easy (4)? Let's stick to Good for now to avoid over-optimizing FSRS too early.
        
        return EvaluationResult(
            is_correct=is_correct,
            quality=quality,
            score_change=score_change,
            feedback={
                'correct_id': correct_id,
                'user_selected': selected_id,
                'time_taken': duration_ms,
                'bonus_awarded': score_change - 10 if is_correct else 0
            }
        )

# File: mindstack_app/modules/vocabulary/modes/mcq_mode.py
"""
MCQ Mode
========
Multiple-choice question mode for vocabulary learning.

Reuses the battle-tested ``MCQEngine`` from the existing
``vocab_mcq`` module for question generation and answer checking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_mode import BaseVocabMode, EvaluationResult


class MCQMode(BaseVocabMode):
    """
    Multiple-choice mode.

    ``format_interaction`` generates N choices (default 4) from the
    item pool.  ``evaluate_submission`` checks the selected index.
    """

    def get_mode_id(self) -> str:
        return 'mcq'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build an MCQ question payload.

        Delegates to ``MCQEngine.generate_question`` so all the
        distractor-selection and shuffling logic is reused.
        """
        from mindstack_app.modules.vocabulary.mcq.engine.mcq_engine import MCQEngine

        settings = settings or {}
        
        # [NEW] Get media folders from container for BBCode resolution
        from mindstack_app.models import LearningContainer
        container_id = item.get('container_id')
        container = LearningContainer.query.get(container_id) if container_id else None
        
        config = {
            'mode': settings.get('direction', 'front_back'),
            'num_choices': settings.get('num_choices', 4),
            'question_key': settings.get('question_key'),
            'answer_key': settings.get('answer_key'),
            'custom_pairs': settings.get('custom_pairs'),
            'audio_folder': container.media_audio_folder if container else None,
            'image_folder': container.media_image_folder if container else None,
        }

        question_data = MCQEngine.generate_question(
            item_data=item,
            all_items_data=all_items or [],
            config=config,
        )

        return {
            'type': 'mcq',
            'question': question_data.get('question', ''),
            'choices': question_data.get('choices', []),
            'choice_item_ids': question_data.get('choice_item_ids', []),
            'correct_index': question_data.get('correct_index', 0),
            'correct_answer': question_data.get('correct_answer', ''),
        }

    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Check the selected answer index against the correct one.
        """
        from mindstack_app.modules.vocabulary.mcq.engine.mcq_engine import MCQEngine
        from mindstack_app.modules.scoring.interface import ScoringInterface

        correct_index = user_input.get('correct_index', 0)
        user_answer_index = user_input.get('answer_index', -1)
        
        # [NEW] Pass central config to engine
        point_value = ScoringInterface.get_score_value('VOCAB_MCQ_CORRECT_BONUS')
        config = {'MCQ_CORRECT_SCORE': point_value}

        result = MCQEngine.check_answer(correct_index, user_answer_index, config=config)

        is_correct = result.get('is_correct', False)

        return EvaluationResult(
            is_correct=is_correct,
            quality=3 if is_correct else 1,       # Good / Again
            score_change=result.get('score_change', 0),
            feedback={
                'correct_index': correct_index,
                'selected_index': user_answer_index,
            },
        )

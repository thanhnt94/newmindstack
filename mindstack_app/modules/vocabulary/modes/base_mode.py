# File: mindstack_app/modules/vocabulary/modes/base_mode.py
"""
Base Vocabulary Mode
====================
Abstract contract for individual learning modes inside the Vocabulary
domain (MCQ, Flashcard, Typing, Listening, Matching, Speed …).

A *Mode* is responsible for two things:

1. **Formatting** a raw ``LearningItem`` dict into a UI-ready
   ``InteractionPayload`` (the *question*).
2. **Evaluating** the learner's submission and returning a grade.

Modes are **stateless** – all context is passed via arguments.
This makes them trivially testable and hot-swappable at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── DTOs specific to mode evaluation ────────────────────────────────


@dataclass
class EvaluationResult:
    """
    Outcome produced by ``BaseVocabMode.evaluate_submission``.

    ``quality`` follows the FSRS convention:
    * 1 = Again  (forgot / wrong)
    * 2 = Hard
    * 3 = Good
    * 4 = Easy

    For binary modes (MCQ, Typing) the mapping is typically:
    * wrong → quality = 1
    * correct → quality = 3
    """

    is_correct: bool
    quality: int                    # 1-4 (FSRS scale)
    score_change: int = 0           # gamification points delta
    breakdown: Dict[str, Any] = field(default_factory=dict) # Detailed score components
    feedback: Dict[str, Any] = field(default_factory=dict)


# ── Abstract Mode ────────────────────────────────────────────────────


class BaseVocabMode(ABC):
    """
    Contract for vocabulary learning modes.

    Subclass checklist:
    * Implement ``get_mode_id``, ``format_interaction``, ``evaluate_submission``.
    * Keep all logic **pure** – no DB access, no Flask context.
    """

    @abstractmethod
    def get_mode_id(self) -> str:
        """
        Return the unique identifier for this mode.

        Examples: ``'flashcard'``, ``'mcq'``, ``'typing'``.
        """
        ...

    @abstractmethod
    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform a raw item dict into a UI-ready interaction payload.

        Args:
            item:      Dict with at least ``item_id``, ``front``, ``back``,
                       ``content`` (JSON blob).
            all_items: Full item list – needed by modes that generate
                       distractors (e.g. MCQ).
            settings:  Mode-specific settings (``num_choices``, ``direction`` …).

        Returns:
            A dict ready to be embedded into
            :pyclass:`InteractionPayload.data`.
        """
        ...

    @abstractmethod
    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Grade the learner's answer.

        Args:
            item:       The original item dict (same as passed to
                        ``format_interaction``).
            user_input: Raw submission from the frontend.
                        Shape depends on mode, e.g.
                        ``{"answer_index": 2}`` for MCQ,
                        ``{"quality": 3}`` for Flashcard.
            settings:   Mode-specific settings.

        Returns:
            :pyclass:`EvaluationResult` with correctness, quality,
            score delta, and optional feedback.
        """
        ...

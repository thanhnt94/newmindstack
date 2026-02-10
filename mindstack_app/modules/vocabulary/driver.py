# File: mindstack_app/modules/vocabulary/driver.py
"""
Vocabulary Session Driver
=========================
Concrete ``BaseSessionDriver`` for all vocabulary-based learning modes
(Flashcard, MCQ, Typing, Listening, Matching, Speed).

Responsibility chain::

    Session  →  VocabularyDriver  →  ModeFactory  →  MCQMode / FlashcardMode / …
                      ↓
                 FSRS Interface  (SRS update after grading)

The driver is **mode-agnostic** – it delegates formatting and grading
to whatever ``BaseVocabMode`` the factory returns for the requested
mode name.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mindstack_app.modules.session.drivers.base import (
    BaseSessionDriver,
    InteractionPayload,
    SessionState,
    SessionSummary,
    SubmissionResult,
)
from .modes.factory import ModeFactory


class VocabularyDriver(BaseSessionDriver):
    """
    Driver for vocabulary-type sessions.

    Works with *any* registered ``BaseVocabMode`` – the concrete mode
    is resolved once via ``ModeFactory.create(state.mode)`` and then
    used for every interaction in the session.
    """

    # ── lifecycle: initialize ────────────────────────────────────────

    def initialize_session(
        self,
        container_id: int,
        user_id: int,
        settings: Dict[str, Any],
    ) -> SessionState:
        """
        Build the item queue for a vocabulary session.

        Steps:
        1. Load all items belonging to *container_id*.
        2. (Optionally) apply FSRS-based filtering via settings['filter'].
        3. Return a ``SessionState`` ready for iteration.
        """
        from mindstack_app.models import LearningItem

        mode = settings.get('mode', 'flashcard')

        # 1. Load items
        items_query = LearningItem.query.filter_by(
            container_id=container_id
        ).order_by(LearningItem.order_in_container.asc())

        item_ids: List[int] = [i.item_id for i in items_query.all()]

        # 2. Apply FSRS filter if requested
        fsrs_filter = settings.get('filter')  # e.g. 'due', 'new', 'mixed'
        if fsrs_filter:
            item_ids = self._apply_fsrs_filter(user_id, item_ids, fsrs_filter)

        # 3. Build state
        state = SessionState(
            user_id=user_id,
            container_id=container_id,
            mode=mode,
            item_queue=item_ids,
            total_items=len(item_ids),
            settings=settings,
        )

        return state

    # ── lifecycle: get_next_interaction ───────────────────────────────

    def get_next_interaction(
        self,
        state: SessionState,
    ) -> Optional[InteractionPayload]:
        """
        Fetch the next item and format it using the active Mode.
        """
        # Check if queue is exhausted
        remaining = [
            iid for iid in state.item_queue
            if iid not in state.processed_ids
        ]

        if not remaining:
            return None

        next_item_id = remaining[0]

        # Load item data from DB
        item_data = self._load_item_data(next_item_id)
        if item_data is None:
            # Skip broken item
            state.processed_ids.append(next_item_id)
            return self.get_next_interaction(state)

        # Load all items for modes that need distractors (MCQ)
        all_items_data = self._load_all_items_data(state.container_id)

        # Resolve mode and format
        mode = ModeFactory.create(state.mode)
        interaction_data = mode.format_interaction(
            item=item_data,
            all_items=all_items_data,
            settings=state.settings,
        )

        # Progress info
        current_pos = len(state.processed_ids) + 1
        is_last = len(remaining) == 1

        return InteractionPayload(
            item_id=next_item_id,
            interaction_type=state.mode,
            data=interaction_data,
            progress={
                'current': current_pos,
                'total': state.total_items,
                'remaining': len(remaining),
            },
            is_last=is_last,
        )

    # ── lifecycle: process_submission ─────────────────────────────────

    def process_submission(
        self,
        state: SessionState,
        item_id: int,
        user_input: Dict[str, Any],
    ) -> SubmissionResult:
        """
        Grade the submission, update FSRS, and mutate session state.
        """
        # 1. Load item
        item_data = self._load_item_data(item_id)

        # 2. Evaluate via Mode
        mode = ModeFactory.create(state.mode)
        evaluation = mode.evaluate_submission(
            item=item_data or {},
            user_input=user_input,
            settings=state.settings,
        )

        # 3. Update FSRS
        srs_update: Optional[Dict[str, Any]] = None
        try:
            from mindstack_app.modules.fsrs.interface import FSRSInterface

            memory_state, srs_result = FSRSInterface.process_review(
                user_id=state.user_id,
                item_id=item_id,
                quality=evaluation.quality,
                mode=state.mode,
                container_id=state.container_id,
            )

            srs_update = {
                'next_due': srs_result.next_due.isoformat() if srs_result.next_due else None,
                'interval': srs_result.interval,
                'stability': srs_result.stability,
            }
        except Exception:
            # FSRS failure should not block the session
            pass

        # 4. Mutate state
        if item_id not in state.processed_ids:
            state.processed_ids.append(item_id)
        if evaluation.is_correct:
            state.correct_count += 1
        else:
            state.incorrect_count += 1

        return SubmissionResult(
            item_id=item_id,
            is_correct=evaluation.is_correct,
            quality=evaluation.quality,
            score_change=evaluation.score_change,
            feedback=evaluation.feedback,
            srs_update=srs_update,
        )

    # ── lifecycle: finalize_session ──────────────────────────────────

    def finalize_session(
        self,
        state: SessionState,
    ) -> SessionSummary:
        """
        Compute session summary statistics.
        """
        total = len(state.processed_ids)
        correct = state.correct_count
        incorrect = state.incorrect_count
        accuracy = (correct / total * 100) if total > 0 else 0.0

        # Calculate duration
        duration = 0.0
        try:
            started = datetime.fromisoformat(state.started_at)
            duration = (datetime.now(timezone.utc) - started).total_seconds()
        except (ValueError, TypeError):
            pass

        return SessionSummary(
            total_items=total,
            correct=correct,
            incorrect=incorrect,
            accuracy=round(accuracy, 1),
            duration_seconds=round(duration, 1),
            xp_earned=correct * 10,  # simple XP formula
        )

    # ── private helpers ──────────────────────────────────────────────

    @staticmethod
    def _load_item_data(item_id: int) -> Optional[Dict[str, Any]]:
        """Load a single LearningItem as a plain dict."""
        from mindstack_app.models import LearningItem

        item = LearningItem.query.get(item_id)
        if item is None:
            return None

        content = item.content or {}
        return {
            'item_id': item.item_id,
            'front': content.get('front', ''),
            'back': content.get('back', ''),
            'content': content,
            'item_type': item.item_type,
            'container_id': item.container_id,
            'order_in_container': item.order_in_container,
        }

    @staticmethod
    def _load_all_items_data(container_id: int) -> List[Dict[str, Any]]:
        """Load all items in a container as plain dicts."""
        from mindstack_app.models import LearningItem

        items = LearningItem.query.filter_by(
            container_id=container_id
        ).order_by(LearningItem.order_in_container.asc()).all()

        return [
            {
                'item_id': i.item_id,
                'front': (i.content or {}).get('front', ''),
                'back': (i.content or {}).get('back', ''),
                'content': i.content or {},
                'item_type': i.item_type,
            }
            for i in items
        ]

    @staticmethod
    def _apply_fsrs_filter(
        user_id: int,
        item_ids: List[int],
        filter_type: str,
    ) -> List[int]:
        """
        Filter and reorder item IDs based on FSRS memory state.

        Supported filters: 'due', 'new', 'mixed', 'hard'.
        Falls back to the original order if the filter is unknown.
        """
        from datetime import datetime, timezone
        from mindstack_app.modules.fsrs.interface import FSRSInterface

        if not item_ids:
            return []

        states = FSRSInterface.batch_get_memory_states(user_id, item_ids)
        now = datetime.now(timezone.utc)

        if filter_type == 'due':
            return [
                iid for iid in item_ids
                if iid in states
                and states[iid].state != 0
                and states[iid].due_date
                and states[iid].due_date <= now
            ]

        elif filter_type == 'new':
            return [
                iid for iid in item_ids
                if iid not in states or states[iid].state == 0
            ]

        elif filter_type == 'hard':
            return [
                iid for iid in item_ids
                if iid in states and states[iid].difficulty >= 7.0
            ]

        elif filter_type == 'mixed':
            # Due items first (shuffled), then new items (sequential)
            import random

            due = [
                iid for iid in item_ids
                if iid in states
                and states[iid].state != 0
                and states[iid].due_date
                and states[iid].due_date <= now
            ]
            new = [
                iid for iid in item_ids
                if iid not in states or states[iid].state == 0
            ]
            random.shuffle(due)
            return due + new

        # Fallback: return as-is
        return item_ids

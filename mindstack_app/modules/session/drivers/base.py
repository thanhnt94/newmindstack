# File: mindstack_app/modules/session/drivers/base.py
"""
Base Session Driver
===================
Abstract contract that every content-type driver must implement.
The Session module only talks to this interface – it never knows
which concrete driver (Vocabulary, Quiz, Course …) is running.

Design principles
-----------------
* **Stateless methods** – all mutable state lives in ``SessionState``
  which is passed around explicitly.
* **Pure data in / data out** – DTOs are plain dataclasses, no ORM
  objects leak across module boundaries.
* **Framework-agnostic** – no Flask imports; the concrete driver may
  use Flask internally, but the contract does not require it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Data Transfer Objects ────────────────────────────────────────────


@dataclass
class SessionState:
    """
    Serialisable snapshot of a running session.

    Drivers populate this on ``initialize_session`` and mutate it on
    every ``process_submission``.  The Session module persists it to
    ``LearningSession.set_id_data`` (JSON column) between requests.
    """

    user_id: int
    container_id: int
    mode: str                                   # e.g. 'flashcard', 'mcq', 'typing'
    session_id: Optional[int] = None
    item_queue: List[int] = field(default_factory=list)  # ordered item_ids
    processed_ids: List[int] = field(default_factory=list)
    correct_count: int = 0
    incorrect_count: int = 0
    total_items: int = 0
    current_index: int = 0
    settings: Dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: Dict[str, Any] = field(default_factory=dict)   # driver-specific data


@dataclass
class InteractionPayload:
    """
    What the frontend receives for the *current* interaction.

    ``interaction_type`` tells the UI which renderer to use
    (``"flashcard"``, ``"mcq"``, ``"typing"`` …).
    ``data`` is a free-form dict whose schema depends on the type.
    """

    item_id: int
    interaction_type: str               # 'flashcard' | 'mcq' | 'typing' | …
    data: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)  # e.g. {current: 3, total: 20}
    is_last: bool = False


@dataclass
class SubmissionResult:
    """Feedback returned to the frontend after a submission."""

    item_id: int
    is_correct: bool
    quality: int                         # FSRS quality 1-4, or binary 0/5
    score_change: int = 0
    feedback: Dict[str, Any] = field(default_factory=dict)   # correct_answer, explanation …
    srs_update: Optional[Dict[str, Any]] = None               # next_due, interval …
    gamification: Dict[str, Any] = field(default_factory=dict) # breakdown, bonuses …


@dataclass
class SessionSummary:
    """Returned when the session ends (``finalize_session``)."""

    total_items: int = 0
    correct: int = 0
    incorrect: int = 0
    accuracy: float = 0.0
    duration_seconds: float = 0.0
    xp_earned: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


# ── Abstract Driver ──────────────────────────────────────────────────


class BaseSessionDriver(ABC):
    """
    Contract for all session drivers.

    Lifecycle::

        state  = driver.initialize_session(container_id, user_id, settings)
        while not done:
            payload = driver.get_next_interaction(state)
            result  = driver.process_submission(state, payload.item_id, user_input)
        summary = driver.finalize_session(state)
    """

    # ── lifecycle methods ────────────────────────────────────────────

    @abstractmethod
    def initialize_session(
        self,
        container_id: int,
        user_id: int,
        settings: Dict[str, Any],
    ) -> SessionState:
        """
        Prepare the learning queue.

        * Load items belonging to *container_id*.
        * Apply FSRS filters / ordering based on *settings* (mode, filter …).
        * Return a populated ``SessionState``.
        """
        ...

    @abstractmethod
    def get_next_interaction(
        self,
        state: SessionState,
    ) -> Optional[InteractionPayload]:
        """
        Return the next interaction for the learner.

        Returns ``None`` when the queue is exhausted.
        """
        ...

    @abstractmethod
    def process_submission(
        self,
        state: SessionState,
        item_id: int,
        user_input: Dict[str, Any],
    ) -> SubmissionResult:
        """
        Grade the learner's submission and update ``state`` in place.

        Concrete drivers are expected to:
        1. Delegate grading to the active *Mode*.
        2. Call ``FSRSInterface.process_review(…)`` to update SRS.
        3. Mutate ``state`` (processed_ids, correct_count …).
        """
        ...

    @abstractmethod
    def finalize_session(
        self,
        state: SessionState,
    ) -> SessionSummary:
        """
        Wrap up the session and return a summary.

        Drivers may emit signals (``session_completed``) here.
        """
        ...

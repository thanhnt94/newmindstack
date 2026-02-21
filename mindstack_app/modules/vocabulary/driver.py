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
from typing import Any, Dict, List, Optional, Union

from mindstack_app.modules.session.interface import (
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
        container_id: Union[int, str],
        user_id: int,
        settings: Dict[str, Any],
    ) -> SessionState:
        """
        Build the item queue for a vocabulary session.

        Steps:
        1. Load all items belonging to *container_id* (or multiple containers).
        2. (Optionally) apply FSRS-based filtering via settings['filter'].
        3. Return a ``SessionState`` ready for iteration.
        """
        from mindstack_app.models import LearningItem
        from .flashcard.engine.algorithms import get_accessible_flashcard_set_ids
        from flask import current_app

        mode = settings.get('mode', 'flashcard')
        current_app.logger.info(f"[VOCAB_DRIVER] Init Session U:{user_id} C:{container_id} Settings:{settings}")
        print(f" [VOCAB_DRIVER] Init Session U:{user_id} C:{container_id} Settings:{settings}")

        # 1. Load items - handle 'all', single ID, or multi-set
        set_ids_override = settings.get('set_ids')
        
        if container_id == 'all' or set_ids_override == 'all':
            # Load all accessible sets for this user
            accessible_ids = get_accessible_flashcard_set_ids(user_id)
            items_query = LearningItem.query.filter(
                LearningItem.container_id.in_(accessible_ids)
            )
            # Use first container as representative ID
            container_id = accessible_ids[0] if accessible_ids else 0
        elif set_ids_override and isinstance(set_ids_override, list):
            # Multi-set scenario
            items_query = LearningItem.query.filter(
                LearningItem.container_id.in_(set_ids_override)
            )
        else:
            # Single container
            items_query = LearningItem.query.filter_by(
                container_id=container_id
            )

        # 2. Apply FSRS filter if requested (DB Level)
        fsrs_filter = settings.get('filter')  # e.g. 'due', 'new', 'mixed', 'srs'
        
        # [FIX] Map 'cram' to 'review' (Learned items, random order)
        if fsrs_filter == 'cram':
            fsrs_filter = 'review'
        
        if fsrs_filter in ['srs', 'mixed', 'mixed_srs', 'due', 'new', 'review', 'available']:
            current_app.logger.info(f"[VOCAB_DRIVER] Applying DB Filter (DYNAMIC): {fsrs_filter}")
            print(f" [VOCAB_DRIVER] Applying DB Filter (DYNAMIC): {fsrs_filter}")
            
            # Since we dynamically fetch on-the-fly, we keep the queue empty.
            item_ids = []
            total_items_estimated = 0
            
        elif fsrs_filter:
            current_app.logger.info(f"[VOCAB_DRIVER] Applying DB Filter: {fsrs_filter}")
            print(f" [VOCAB_DRIVER] Applying DB Filter: {fsrs_filter}")
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            items_query = FSRSInterface.apply_memory_filter(items_query, user_id, fsrs_filter)
            item_ids = [i.item_id for i in items_query.all()]
            total_items_estimated = 0
        else:
            # Default sort if no filter
            print(f" [VOCAB_DRIVER] NO FILTER SET! Using default sequential sort.")
            items_query = items_query.order_by(LearningItem.container_id.asc(), LearningItem.order_in_container.asc())
            item_ids = [i.item_id for i in items_query.all()]
            total_items_estimated = 0
            if 2640 in item_ids: print(f" [VOCAB_DRIVER] Item 2640 found in unfiltered sequential list.")
        
        current_app.logger.info(f"[VOCAB_DRIVER] Optimized Session Init: {len(item_ids)} items statically loaded.")
        print(f" [VOCAB_DRIVER] Optimized Session Init: {len(item_ids)} items statically loaded.")

        # 3. Build state
        state = SessionState(
            user_id=user_id,
            container_id=container_id,
            mode=mode,
            item_queue=item_ids,
            total_items=total_items_estimated,
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
        # Check if queue is exhausted or dynamically loading
        remaining = [
            iid for iid in state.item_queue
            if iid not in state.processed_ids
        ]

        next_item_id = None
        is_last = False

        if remaining:
            next_item_id = remaining[0]
            is_last = len(remaining) == 1
        elif state.settings.get('filter') in ['due', 'new', 'review', 'available', 'srs', 'mixed', 'mixed_srs']:
            # DYNAMIC FETCH: Fallback to FlashcardEngine to fetch the next best item if queue is empty
            from mindstack_app.modules.vocabulary.flashcard.engine.core import FlashcardEngine
            set_ids_override = state.settings.get('set_ids')
            target_set_ids = set_ids_override if set_ids_override else [state.container_id]
            
            # Use 'state.settings.get('filter')' or 'state.mode' as the fetch mode?
            # FlashcardEngine expects the mode ID (like 'srs', 'new')
            # state.settings['filter'] usually holds the FSRS mode. Default to state.mode.
            fetch_mode = state.settings.get('filter') or state.mode
            
            batch_data = FlashcardEngine.get_next_batch(
                user_id=state.user_id,
                set_id=target_set_ids,
                mode=fetch_mode,
                processed_ids=state.processed_ids,
                batch_size=1
            )
            
            if batch_data and batch_data.get('items'):
                next_item_id = batch_data['items'][0].get('item_id')
                # If we dynamically fetch, we aren't completely sure if it's the last one
                # unless we check total_items_in_session remaining, but typically dynamic means potentially endless until 0
                is_last = False 
                
                # Update total items dynamically if engine returned it
                estimated_total = batch_data.get('total_items_in_session')
                if estimated_total is not None and estimated_total > state.total_items:
                    state.total_items = estimated_total

        if not next_item_id:
            return None

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
        # For dynamic modes where remaining is empty, estimate remaining
        remaining_count = len(remaining) if remaining else max(0, state.total_items - len(state.processed_ids))

        return InteractionPayload(
            item_id=next_item_id,
            interaction_type=state.mode,
            data=interaction_data,
            progress={
                'current': current_pos,
                'total': state.total_items,
                'remaining': remaining_count,
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
        from flask import current_app
        current_app.logger.info(f"[VOCAB_DRIVER] Processing submission User {state.user_id} Item {item_id} Input {user_input}")
        print(f" [VOCAB_DRIVER] Processing submission User {state.user_id} Item {item_id} Input {user_input}")

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

            # 3. Update FSRS (Standard) and Record Deep Analytics (New)
            
            # [Step 1] Pre-calculation (Before FSRS Update)
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
            
            # Fetch Pre-state (Snapshot)
            pre_state = FSRSInterface.get_item_state(state.user_id, item_id)
            pre_stability = pre_state.stability if pre_state else 0.0
            pre_difficulty = pre_state.difficulty if pre_state else 0.0
            pre_reps = pre_state.repetitions if pre_state else 0
            
            # Calculate Retrievability (Pre-answer)
            pre_retrievability = FSRSInterface.get_retrievability(pre_state) if pre_state else 0.0
            
            # Count Mode Reps via Interface
            reps_mode = LearningHistoryInterface.count_mode_reps(
                user_id=state.user_id, 
                item_id=item_id, 
                learning_mode=state.mode
            )

            # [Step 2] Scoring (Already done in mode.evaluate_submission)
            # evaluation.breakdown is available
            raw_bd = getattr(evaluation, 'breakdown', {})
            flat_bd = {}
            if raw_bd:
                flat_bd['base'] = raw_bd.get('base', 0)
                mods = raw_bd.get('modifiers', {})
                if isinstance(mods, dict):
                    for k, v in mods.items():
                        flat_bd[k] = v
                else:
                    # In case modifiers isn't a dict (shouldn't happen with ScoreCalculator)
                    pass
            else:
                flat_bd['base'] = evaluation.score_change

            gamification_snapshot = {
                'total_score': evaluation.score_change,
                'breakdown': flat_bd
            }
            
            # [Step 3] Algorithm Update
            memory_state, srs_result = FSRSInterface.process_review(
                user_id=state.user_id,
                item_id=item_id,
                quality=evaluation.quality,
                mode=state.mode,
                container_id=state.container_id,
            )
            current_app.logger.info(f"[VOCAB_DRIVER] FSRS Update Success: Stb={srs_result.stability}, Due={srs_result.next_review}")

            # [Step 4] Recording (Deep Analytics)
            try:
                from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
                
                result_data = {
                    'rating': evaluation.quality,
                    'user_answer': user_input.get('user_answer'),
                    'is_correct': evaluation.is_correct,
                    'review_duration': user_input.get('duration_ms', 0)
                }
                
                context_data = {
                    'session_id': state.session_id,
                    'container_id': state.container_id,
                    'learning_mode': state.mode
                }
                
                # A. FSRS Snapshot (Audit)
                fsrs_snapshot = {
                    'scheduler_ver': '5.0', # Hardcoded or from config
                    'card_state': memory_state.state, 
                    'retrievability': round(pre_retrievability, 4), # Pre-R is what matters for algorithm audit
                    'scheduled_days': srs_result.interval_minutes / 1440.0, # Approximation or store interval
                    'elapsed_days': 0.0, # Need calculation if strictly required, but R implies it
                    
                    # Pre-values
                    'pre_stability': round(pre_stability, 4),
                    'pre_difficulty': round(pre_difficulty, 4),
                    
                    # Post-values
                    'post_stability': round(srs_result.stability, 4),
                    'post_difficulty': round(srs_result.difficulty, 4)
                }
                
                # B. Context Snapshot (Behavior)
                context_snapshot = {
                    'mode': state.mode,
                    'input_device': 'unknown', # TODO: Capture from headers/user_input
                    
                    # Counters
                    'reps_global': pre_reps,
                    'reps_mode': reps_mode,
                    'reps_session': 1, # TODO: Track in session state if needed
                    
                    # Behavior
                    'is_first_ever': (pre_reps == 0),
                    'is_first_mode': (reps_mode == 0),
                    'is_leech': (pre_state.data.get('is_leech', False) if pre_state and pre_state.data else False),
                    
                    # Performance
                    'thinking_time': user_input.get('duration_ms', 0)
                }
                
                # C. Gamification Snapshot (Breakdown)
                # Calculated above
                
                LearningHistoryInterface.record_log(
                    user_id=state.user_id,
                    item_id=item_id,
                    result_data=result_data,
                    context_data=context_data,
                    fsrs_snapshot=fsrs_snapshot,
                    game_snapshot=gamification_snapshot,
                    context_snapshot=context_snapshot
                )
                current_app.logger.info(f"[VOCAB_DRIVER] Deep Analytics Log recorded for session {state.session_id}")
            except Exception as e:
                current_app.logger.error(f"[VOCAB_DRIVER] Failed to record StudyLog: {e}", exc_info=True)
                # Don't fail the whole request, just log error

            # Fetch stats for HUD display
            try:
                from .flashcard.engine.core import FlashcardEngine
                full_stats = FlashcardEngine.get_item_statistics(
                    state.user_id, item_id
                )
                
                # Build srs_update with all necessary metrics
                srs_update = {
                    'next_due': srs_result.next_review.isoformat() if srs_result.next_review else None,
                    'interval': srs_result.interval_minutes,
                    'stability': full_stats.get('stability', srs_result.stability),
                    'difficulty': full_stats.get('difficulty', srs_result.difficulty),
                    'retrievability': full_stats.get('retrievability', 0),
                    'repetitions': srs_result.repetitions, 
                    'times_reviewed': srs_result.repetitions, 
                    'status': full_stats.get('status', 'new'),
                    'display': full_stats.get('display', {}), # For immediate HUD display-ready strings
                }
            except Exception as e:
                current_app.logger.error(f"[VOCAB_DRIVER] Error fetching stats: {e}")
                print(f" [VOCAB_DRIVER] Error fetching stats: {e}")
                # Fallback to basic SRS result if stats fetch fails
                srs_update = {
                    'next_due': srs_result.next_review.isoformat() if srs_result.next_review else None,
                    'interval': srs_result.interval_minutes,
                    'stability': srs_result.stability,
                    'difficulty': srs_result.difficulty,
                    'retrievability': 0,
                    'repetitions': 0,
                }

        except Exception as e:
            # FSRS failure should be logged
            current_app.logger.error(f"[VOCAB_DRIVER] FSRS/Logging Update FAILED: {e}", exc_info=True)
            print(f" [VOCAB_DRIVER] FSRS Update FAILED: {e}")

        # 4. Mutate state
        if item_id not in state.processed_ids:
            state.processed_ids.append(item_id)
        if evaluation.is_correct:
            state.correct_count += 1
        else:
            state.incorrect_count += 1

        # 5. Emit signal for Global Scoring [NEW]
        try:
            from mindstack_app.core.signals import card_reviewed
            from mindstack_app.models import LearningItem
            
            # Fetch item type for signal
            item = LearningItem.query.get(item_id)
            item_type = item.item_type if item else 'FLASHCARD'
            
            card_reviewed.send(
                None,
                user_id=state.user_id,
                item_id=item_id,
                quality=evaluation.quality,
                is_correct=evaluation.is_correct,
                learning_mode=state.mode,
                score_points=evaluation.score_change,
                item_type=item_type,
                reason=f"Vocab {state.mode.capitalize()} Practice"
            )
            current_app.logger.info(f"[VOCAB_DRIVER] card_reviewed signal emitted for user {state.user_id}, points {evaluation.score_change}")
        except Exception as e:
            current_app.logger.error(f"[VOCAB_DRIVER] Failed to emit card_reviewed signal: {e}")

        frontend_gamification = {
            'total_score': evaluation.score_change,
            'breakdown': gamification_snapshot['breakdown']
        }

        return SubmissionResult(
            item_id=item_id,
            is_correct=evaluation.is_correct,
            quality=evaluation.quality,
            score_change=evaluation.score_change,
            feedback=evaluation.feedback,
            srs_update=srs_update,
            gamification=frontend_gamification
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



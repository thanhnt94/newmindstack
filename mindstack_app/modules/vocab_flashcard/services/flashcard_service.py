# File: mindstack_app/modules/vocab_flashcard/services/flashcard_service.py
"""
FlashcardService - Orchestration Facade
========================================
Provides a high-level API for flashcard learning operations.
Delegates to FSRSInterface for scheduling and SessionInterface for tracking.

This service acts as the single entry point for answer processing,
ensuring proper coordination between modules.
"""

from typing import Optional, Dict, Any, Tuple
from flask import current_app

from mindstack_app.models import LearningItem
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.session.interface import SessionInterface
from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine
from mindstack_app.modules.learning_history.services import HistoryRecorder
from mindstack_app.core.signals import card_reviewed
from mindstack_app.utils.db_session import safe_commit


class FlashcardService:
    """
    Orchestrates flashcard learning operations.
    
    This service coordinates between:
    - fsrs.interface: Spaced repetition scheduling
    - session.interface: Session progress tracking
    - learning_history: Interaction recording
    - gamification: Score calculation (via signals)
    """
    
    @classmethod
    def submit_answer(
        cls,
        user_id: int,
        session_id: int,
        item_id: int,
        quality: int,
        duration_ms: int = 0,
        user_answer_text: Optional[str] = None,
        container_id: Optional[int] = None,
        learning_mode: str = 'flashcard'
    ) -> Dict[str, Any]:
        """
        Process a flashcard answer with full integration.
        
        Args:
            user_id: The user's ID
            session_id: The active session ID
            item_id: The item being reviewed
            quality: FSRS quality rating (1-4)
            duration_ms: Time spent on the card in milliseconds
            user_answer_text: Optional text of user's answer
            container_id: Optional container ID override
            learning_mode: Learning mode identifier
            
        Returns:
            Dictionary with processing results:
            - success: bool
            - score_change: int
            - result_type: 'correct' | 'incorrect' | 'vague'
            - srs_data: dict with next_review, interval info
            - error: str (only if success=False)
        """
        try:
            # 1. Validate item exists
            item = LearningItem.query.get(item_id)
            if not item:
                return {
                    'success': False,
                    'error': f'Item {item_id} not found'
                }
            
            resolved_container_id = container_id or item.container_id
            
            # 2. Determine result type from quality
            if quality >= 4:
                result_type = 'correct'
            elif quality >= 2:
                result_type = 'vague'
            else:
                result_type = 'incorrect'
            
            # 3. Schedule via FSRS
            state_record, srs_result = FSRSInterface.process_review(
                user_id=user_id,
                item_id=item_id,
                quality=quality,
                mode='flashcard',
                duration_ms=duration_ms,
                container_id=resolved_container_id,
                learning_mode=learning_mode
            )
            
            # 4. Calculate score
            is_correct = (quality >= 3)
            score_result = ScoringEngine.calculate_answer_points(
                mode='flashcard',
                quality=quality,
                is_correct=is_correct,
                correct_streak=state_record.streak if state_record else 0,
                stability=state_record.stability if state_record else 0,
                difficulty=state_record.difficulty if state_record else 0
            )
            score_change = score_result.total_points
            
            # 5. Update session progress
            SessionInterface.update_progress(
                session_id=session_id,
                item_id=item_id,
                result_type=result_type,
                points=score_change
            )
            
            # 6. Record history
            fsrs_snapshot = None
            if state_record and srs_result:
                fsrs_snapshot = {
                    'stability': srs_result.stability,
                    'difficulty': srs_result.difficulty,
                    'state': srs_result.state,
                    'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None
                }
            
            HistoryRecorder.record_interaction(
                user_id=user_id,
                item_id=item_id,
                result_data={
                    'rating': quality,
                    'user_answer': user_answer_text,
                    'is_correct': is_correct,
                    'review_duration': duration_ms
                },
                context_data={
                    'session_id': session_id,
                    'container_id': resolved_container_id,
                    'learning_mode': learning_mode
                },
                fsrs_snapshot=fsrs_snapshot,
                game_snapshot={'score_earned': score_change}
            )
            
            # 7. Emit signal for gamification
            card_reviewed.send(
                None,
                user_id=user_id,
                item_id=item_id,
                quality=quality,
                is_correct=is_correct,
                learning_mode=learning_mode,
                score_points=score_change,
                item_type='FLASHCARD',
                reason=f"Flashcard Answer (Quality: {quality})"
            )
            
            # 8. Commit
            from mindstack_app.models import db
            safe_commit(db.session)
            
            # 9. Build response
            srs_data = None
            if srs_result:
                srs_data = {
                    'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None,
                    'interval_minutes': srs_result.interval_minutes
                }
            
            return {
                'success': True,
                'score_change': score_change,
                'result_type': result_type,
                'srs_data': srs_data,
                'state': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(
                    state_record.state if state_record else 0, 'new'
                )
            }
            
        except Exception as e:
            current_app.logger.error(
                f"FlashcardService.submit_answer error: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_preview_intervals(user_id: int, item_id: int) -> Dict[str, Any]:
        """
        Get FSRS preview intervals for an item.
        
        Delegates entirely to FSRSInterface.
        """
        return FSRSInterface.get_preview_intervals(user_id, item_id)

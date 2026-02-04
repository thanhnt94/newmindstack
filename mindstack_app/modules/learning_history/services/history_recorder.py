# File: mindstack_app/modules/learning_history/services/history_recorder.py
from typing import Dict, Any, Optional
from mindstack_app.core.extensions import db
from ..models import StudyLog

class HistoryRecorder:
    """
    Scribe service dedicated to recording learning history.
    """
    
    @staticmethod
    def record_interaction(
        user_id: int,
        item_id: int,
        result_data: Dict[str, Any],
        context_data: Dict[str, Any],
        fsrs_snapshot: Optional[Dict[str, Any]] = None,
        game_snapshot: Optional[Dict[str, Any]] = None
    ) -> StudyLog:
        """
        Record a learning interaction (StudyLog).
        
        Args:
            user_id: ID of the user
            item_id: ID of the learning item
            result_data: {rating, user_answer, is_correct, review_duration}
            context_data: {session_id, container_id, learning_mode}
            fsrs_snapshot: State of FSRS parameters after review
            game_snapshot: Points earned, streak info
        """
        log = StudyLog(
            user_id=user_id,
            item_id=item_id,
            
            # Performance
            rating=result_data.get('rating', 0),
            user_answer=result_data.get('user_answer'),
            is_correct=result_data.get('is_correct', False),
            review_duration=result_data.get('review_duration', 0),
            
            # Context
            session_id=context_data.get('session_id'),
            container_id=context_data.get('container_id'),
            learning_mode=context_data.get('learning_mode'),
            
            # Snapshots
            fsrs_snapshot=fsrs_snapshot,
            gamification_snapshot=game_snapshot
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log

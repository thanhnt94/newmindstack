# File: mindstack_app/modules/fsrs/interface.py
from typing import Optional, Tuple, List, Dict, Any
import datetime
from .engine.processor import FSRSProcessor
from .services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from .schemas import SrsResultDTO, CardStateDTO

class FSRSInterface:
    """Public API for FSRS module."""
    
    @staticmethod
    def process_review(
        user_id: int,
        item_id: int,
        quality: int,
        mode: str = 'flashcard',
        duration_ms: int = 0,
        container_id: int = None,
        **kwargs
    ) -> Tuple[Any, SrsResultDTO]:
        """Process a learning interaction and return updated progress and result."""
        return FSRSProcessor.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            duration_ms=duration_ms,
            container_id=container_id,
            **kwargs
        )

    # Legacy alias
    process_answer = process_review

    @staticmethod
    def get_retrievability(progress: Any) -> float:
        """Calculate current retrievability (memory power)."""
        return FSRSProcessor.get_retrievability(progress)

    @staticmethod
    def train_user_parameters(user_id: int) -> Optional[List[float]]:
        """Train and save optimized parameters for a user."""
        return FSRSOptimizerService.train_for_user(user_id)

    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """Get FSRS configuration."""
        return FSRSSettingsService.get(key, default)

    @staticmethod
    def process_interaction(
        user_id: int,
        item_id: int,
        mode: str,
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        High-level wrapper to process any learning interaction.
        Maps mode-specific result_data to FSRS parameters.
        """
        # Determine quality and duration from result_data
        is_correct = result_data.get('is_correct', False)
        duration_ms = result_data.get('duration_ms', 0)
        
        # Default mapping: Correct=Good(3), Incorrect=Again(1)
        quality = 3 if is_correct else 1
        
        # Forward to processor
        progress, srs_result = FSRSInterface.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            duration_ms=duration_ms,
            **result_data # Pass extra context (target_text, etc)
        )
        
        # Return summary dict for UI
        return {
            'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None,
            'interval_days': round(srs_result.interval_minutes / 1440.0, 2),
            'retrievability': round(srs_result.retrievability * 100, 1),
            'state': srs_result.state
        }

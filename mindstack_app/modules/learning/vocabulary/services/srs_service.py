from mindstack_app.modules.learning.core.services.srs_service import SrsService as CoreSrsService
from mindstack_app.models import LearningItem, FlashcardProgress
from flask import current_app
import datetime

class VocabularySrsService:
    """
    Centralized SRS Service for Vocabulary Module.
    Handles grading normalization logic ("Cognitive Load Heuristic") and delegates 
    progress updates to the core SrsService.
    """

    @staticmethod
    def process_interaction(user_id: int, item_id: int, mode: str, result_data: dict):
        """
        Process a user's learning interaction and update SRS progress.

        Args:
            user_id (int): ID of the user.
            item_id (int): ID of the learning item.
            mode (str): The learning mode ('flashcard', 'listening', 'mcq', 'matching', 'typing').
            result_data (dict): Data about the interaction result. 
                                Keys vary by mode (e.g. 'quality', 'accuracy', 'is_correct').

        Returns:
            dict: Summary of the update (quality, new_status, next_review).
        """
        # 1. Normalize Performance to SRS Quality (0-5)
        quality = VocabularySrsService._calculate_srs_quality(mode, result_data)

        # 2. Update Progress via Core Service
        # We pass the specific 'mode' as the source for logging history
        progress = CoreSrsService.update_item_progress(
            user_id=user_id, 
            item_id=item_id, 
            quality=quality, 
            source_mode=mode
        )

        return {
            'quality': quality,
            'status': progress.status,
            'next_review': progress.due_time,
            'score_change': VocabularySrsService._calculate_gamification_score(mode, quality)
        }

    @staticmethod
    def _calculate_srs_quality(mode: str, result_data: dict) -> int:
        """
        Implements the "Cognitive Load Heuristic" to map mode-specific results 
        to standard SRS Quality (0-5).

        Strategy:
        - Flashcard: User Self-Report (1-5).
        - MCQ/Matching (Recognition): Correct -> 4 (Good), Wrong -> 1 (Fail).
        - Listening/Typing (Production): 100% Acc -> 5 (Perfect), >85% -> 4 (Good), else 1 (Fail).
        """
        mode = mode.lower()

        # --- FLASHCARD (Direct Self-Report) ---
        if mode == 'flashcard':
            # flashcard passes 'quality' directly (mapped from buttons in frontend/logic)
            # or 'rating' string: 'again', 'hard', 'good', 'easy'
            if 'quality' in result_data:
                return int(result_data['quality'])
            
            # Map string ratings if present
            rating_map = {
                'fail': 0, 'again': 1, 
                'hard': 3, 'vague': 2, # 'vague' is legacy custom
                'good': 4, 'easy': 5, 'very_easy': 5
            }
            rating = str(result_data.get('rating', 'good')).lower()
            return rating_map.get(rating, 4)

        # --- MCQ / MATCHING (Recognition - Low Cognitive Load) ---
        elif mode in ['mcq', 'quiz', 'matching']:
            is_correct = result_data.get('is_correct', False) or result_data.get('correct', False)
            if is_correct:
                return 4  # Good (Safe maintenance, doesn't boost EF too aggressively)
            else:
                return 1  # Fail

        # --- LISTENING / TYPING (Production - High Cognitive Load) ---
        elif mode in ['listening', 'typing']:
            # Expecting 'accuracy' (0.0 - 1.0)
            accuracy = float(result_data.get('accuracy', 0))
            is_correct = result_data.get('correct', False)

            if accuracy >= 1.0: # Exact match
                return 5  # Perfect (Boosts EF)
            elif accuracy >= 0.85: # Minor typo / Close enough
                return 4  # Good
            else:
                return 1  # Fail

        # Fallback default
        return 4 

    @staticmethod
    def _calculate_gamification_score(mode: str, quality: int) -> int:
        """
        Optional helper to determine score points for gamification based on SRS quality.
        (Reuse existing config logic or simplify here).
        """
        # Simplified scoring for now
        if quality >= 5: return 20
    @staticmethod
    def calculate_retention_rate(last_reviewed: datetime.datetime, interval_minutes: int) -> int:
        """
        Calculate the current retention probability (Memory Strength) based on the 
        Forgetting Curve equation: R = e^(-t/S)
        
        Where:
        - t is time elapsed since last review.
        - S is memory stability (Interval / ln(0.9)). 
          (Assuming 90% retention at the end of the interval).
        
        Returns:
            int: Percentage (0-100).
        """
        if not last_reviewed or interval_minutes <= 0:
            return 0
            
        import math
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Ensure last_reviewed is timezone aware
        if last_reviewed.tzinfo is None:
            last_reviewed = last_reviewed.replace(tzinfo=datetime.timezone.utc)
            
        elapsed_minutes = (now - last_reviewed).total_seconds() / 60
        
        if elapsed_minutes < 0: elapsed_minutes = 0
        
        # Stability (S) calculation
        # If we target 90% retention at the exact due time (t = interval):
        # 0.9 = e^(-interval / S)  =>  ln(0.9) = -interval / S  => S = -interval / ln(0.9)
        # constant -1 / ln(0.9) is approx 9.49
        
        # However, new items (interval=0) handle separately above.
        
        stability = -interval_minutes / math.log(0.9)
        
        # Retention R = e^(-elapsed / stability)
        retention = math.exp(-elapsed_minutes / stability)
        
        return int(retention * 100)


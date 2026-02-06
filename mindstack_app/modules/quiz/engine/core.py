# File: quiz/engine/core.py
# QuizEngine - Logic for quiz question generation and answer processing

import random
from mindstack_app.models import LearningItem, db
from mindstack_app.modules.vocab_mcq.interface import get_available_content_keys, generate_mcq_question
from ..logics.quiz_logic import process_quiz_answer

class QuizEngine:
    """
    Centralized engine for Quiz learning logic.
    Follows Spec v7 refined architecture.
    """

    @staticmethod
    def get_available_content_keys(container_id: int) -> list:
        """Scan items in the container to find available content keys."""
        return get_available_content_keys(container_id)

    @classmethod
    def generate_question(cls, item_dict, all_items_pool, mode='front_back', custom_pairs=None):
        """
        Generate a question object compatible with the Quiz UI.
        Works for both QUIZ_MCQ and Flashcard-based quiz items.
        """
        # If it's already a MCQ item (with choices) or needs generation
        # Use mcq_logic to generate a set of choices
        return generate_mcq_question(
            item_dict, 
            all_items_pool, 
            num_choices=4, 
            mode=mode,
            custom_pairs=custom_pairs
        )

    @classmethod
    def check_answer(cls, item_id, user_answer, user_id, duration_ms=0, 
                    user_answer_key=None, session_id=None, container_id=None, 
                    mode=None, streak_position=0, correct_answer_override=None):
        """
        Process a quiz answer and return results for the UI.
        Delegates to quiz_logic for state updates and scoring.
        """
        # Fetch current user score for return value (UI needs it)
        from mindstack_app.models import User
        user = db.session.get(User, user_id)
        current_score = user.total_score if user else 0
        
        # Use common quiz processing logic
        score_change, new_total_score, is_correct, correct_answer_text, explanation = process_quiz_answer(
            user_id=user_id,
            item_id=item_id,
            user_answer_text=user_answer,
            current_user_total_score=current_score,
            session_id=session_id,
            container_id=container_id,
            mode=mode,
            correct_answer_override=correct_answer_override
        )
        
        # Build result dictionary matching QuizSessionManager expectations
        return {
            'correct': is_correct,
            'score_change': score_change,
            'correct_answer': correct_answer_text,
            'explanation': explanation,
            'mastery_delta': 2.0 if is_correct else -5.0, # Dummy values for UI
            'new_mastery_pct': 50.0, # Dummy
            'points_breakdown': {
                'base': score_change,
                'bonus': 0
            },
            'srs_result': None # Quiz doesn't usually update SRS directly in the same way as Flashcards
        }

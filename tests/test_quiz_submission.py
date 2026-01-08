"""
Tests for Quiz Submission Flow

Tests cover:
- SRS Service interaction processing  
- Quality normalization for quiz mode
- Score calculation and points breakdown
- Progress updates
"""

import pytest
from unittest.mock import patch, MagicMock
import datetime

from mindstack_app.modules.learning.logics.srs_engine import SrsEngine, SrsConstants
from mindstack_app.modules.learning.logics.memory_engine import MemoryEngine


class TestQuizQualityNormalization:
    """Test quality normalization for quiz/MCQ mode."""
    
    def test_quiz_correct_returns_4(self):
        """Correct quiz answer should normalize to quality 4."""
        quality = SrsEngine.normalize_quality('quiz', {'is_correct': True})
        assert quality == 4
    
    def test_quiz_correct_via_correct_key(self):
        """Support 'correct' key as well as 'is_correct'."""
        quality = SrsEngine.normalize_quality('quiz', {'correct': True})
        assert quality == 4
    
    def test_quiz_incorrect_returns_1(self):
        """Incorrect quiz answer should normalize to quality 1."""
        quality = SrsEngine.normalize_quality('quiz', {'is_correct': False})
        assert quality == 1
    
    def test_mcq_same_as_quiz(self):
        """MCQ mode should behave same as quiz."""
        quiz_correct = SrsEngine.normalize_quality('quiz', {'is_correct': True})
        mcq_correct = SrsEngine.normalize_quality('mcq', {'is_correct': True})
        assert quiz_correct == mcq_correct
    
    def test_matching_same_as_quiz(self):
        """Matching mode should behave same as quiz."""
        quiz_correct = SrsEngine.normalize_quality('quiz', {'is_correct': True})
        matching_correct = SrsEngine.normalize_quality('matching', {'is_correct': True})
        assert quiz_correct == matching_correct


class TestQuizProgressUpdate:
    """Test progress updates for quiz mode."""
    
    def test_correct_answer_increases_reps(self):
        """Correct answer should increase repetitions."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=10,
            current_ef=2.5,
            current_reps=1,
            quality=4  # Good (quiz correct)
        )
        
        assert reps == 2
    
    def test_incorrect_answer_resets_reps(self):
        """Incorrect answer should reset to learning."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=60,
            current_ef=2.5,
            current_reps=3,
            quality=1  # Fail (quiz incorrect)
        )
        
        assert status == 'learning'
        assert reps == 0
    
    def test_reviewing_item_correct(self):
        """Reviewing item with correct answer should increase interval."""
        initial_interval = 1440
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=initial_interval,
            current_ef=2.5,
            current_reps=5,
            quality=4
        )
        
        assert interval > initial_interval
        assert status == 'reviewing'
    
    def test_reviewing_item_incorrect_back_to_learning(self):
        """Reviewing item with incorrect answer should go back to learning."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=1440,
            current_ef=2.5,
            current_reps=5,
            quality=1
        )
        
        assert status == 'learning'
        assert reps == 0


class TestMemoryEngineQuizIntegration:
    """Test MemoryEngine quiz answer mapping."""
    
    def test_quiz_correct_quality(self):
        """Correct quiz answer should map to positive quality."""
        quality = MemoryEngine.quiz_answer_to_quality(is_correct=True)
        assert quality >= 3  # Should be passing quality
    
    def test_quiz_incorrect_quality(self):
        """Incorrect quiz answer should map to failing quality."""
        quality = MemoryEngine.quiz_answer_to_quality(is_correct=False)
        assert quality < 3  # Should be failing quality


class TestBatchSubmission:
    """Test batch answer submission scenarios."""
    
    def test_multiple_correct_answers_pattern(self):
        """Multiple correct answers should show consistent behavior."""
        results = []
        for i in range(5):
            status, interval, ef, reps = SrsEngine.calculate_next_state(
                current_status='learning' if i == 0 else 'learning',
                current_interval=10,
                current_ef=2.5,
                current_reps=i,
                quality=4
            )
            results.append(reps)
        
        # Reps should increment consistently
        for i in range(len(results) - 1):
            assert results[i + 1] == results[i] + 1
    
    def test_mixed_answers_pattern(self):
        """Mixed correct/incorrect answers pattern."""
        # Start with correct
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=10,
            current_ef=2.5,
            current_reps=0,
            quality=4
        )
        assert reps == 1
        
        # Then incorrect - should reset
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=60,
            current_ef=2.5,
            current_reps=2,
            quality=1
        )
        assert reps == 0
        
        # Then correct again - should start from 1
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=10,
            current_ef=2.5,
            current_reps=0,
            quality=4
        )
        assert reps == 1


class TestQuizScoring:
    """Test quiz scoring scenarios."""
    
    def test_is_correct_utility(self):
        """Test is_correct utility function."""
        # Quality 3+ is correct
        assert SrsEngine.is_correct(4) is True
        assert SrsEngine.is_correct(5) is True
        assert SrsEngine.is_correct(3) is True
        
        # Quality < 3 is incorrect
        assert SrsEngine.is_correct(2) is False
        assert SrsEngine.is_correct(1) is False
        assert SrsEngine.is_correct(0) is False
    
    def test_quality_description_for_quiz(self):
        """Quiz quality should have meaningful descriptions."""
        # Correct quiz answer (quality 4)
        desc = SrsEngine.quality_to_description(4)
        assert desc == "Good"
        
        # Incorrect quiz answer (quality 1)
        desc = SrsEngine.quality_to_description(1)
        assert "Again" in desc or "Fail" in desc

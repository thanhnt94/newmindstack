"""
Tests for SRS Engine - Spaced Repetition System Logic

Tests cover:
- SM-2 algorithm state transitions
- Interval calculations
- Quality normalization
- Retention/forgetting curve calculations
"""

import pytest
import math
import datetime

from mindstack_app.modules.learning.logics.srs_engine import (
    SrsEngine,
    SrsConstants,
    LearningMode
)


class TestSrsConstants:
    """Test SRS Constants are properly defined."""
    
    def test_default_easiness_factor(self):
        assert SrsConstants.DEFAULT_EASINESS_FACTOR == 2.5
        
    def test_min_easiness_factor(self):
        assert SrsConstants.MIN_EASINESS_FACTOR == 1.3
        
    def test_learning_steps_exist(self):
        assert len(SrsConstants.LEARNING_STEPS_MINUTES) > 0
        
    def test_learning_steps_increase(self):
        """Learning steps should increase in duration."""
        steps = SrsConstants.LEARNING_STEPS_MINUTES
        for i in range(1, len(steps)):
            assert steps[i] > steps[i-1]


class TestSrsEngineCalculateNextState:
    """Test SM-2 algorithm state transitions."""
    
    def test_new_item_correct_starts_learning(self):
        """New item with correct answer should start learning phase."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='new',
            current_interval=0,
            current_ef=2.5,
            current_reps=0,
            quality=4
        )
        
        assert status == 'learning'
        assert reps == 1
        assert interval == SrsConstants.LEARNING_STEPS_MINUTES[0]
    
    def test_new_item_fail_stays_learning(self):
        """New item with incorrect answer should stay in learning."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='new',
            current_interval=0,
            current_ef=2.5,
            current_reps=0,
            quality=2
        )
        
        assert status == 'learning'
        assert reps == 0
        assert interval == SrsConstants.RELEARNING_STEP_MINUTES
    
    def test_learning_progress_through_steps(self):
        """Learning items should progress through learning steps."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=10,
            current_ef=2.5,
            current_reps=1,
            quality=4
        )
        
        assert status == 'learning'
        assert reps == 2
        assert interval == SrsConstants.LEARNING_STEPS_MINUTES[1]
    
    def test_learning_fail_resets_reps(self):
        """Failing in learning phase should reset repetitions."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='learning',
            current_interval=60,
            current_ef=2.5,
            current_reps=3,
            quality=1
        )
        
        assert status == 'learning'
        assert reps == 0
        assert interval == SrsConstants.RELEARNING_STEP_MINUTES
    
    def test_reviewing_correct_increases_interval(self):
        """Correct answer in reviewing should increase interval."""
        initial_interval = 1440  # 1 day
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=initial_interval,
            current_ef=2.5,
            current_reps=5,
            quality=4
        )
        
        assert status == 'reviewing'
        assert interval > initial_interval
        assert reps == 6
    
    def test_reviewing_fail_back_to_learning(self):
        """Failed review should send item back to learning."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=1440,
            current_ef=2.5,
            current_reps=5,
            quality=2
        )
        
        assert status == 'learning'
        assert reps == 0
        assert ef < 2.5  # EF should decrease on failure
        assert ef >= SrsConstants.MIN_EASINESS_FACTOR
    
    def test_ef_increases_with_high_quality(self):
        """EF should increase with high quality answers."""
        _, _, ef5, _ = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=1440,
            current_ef=2.5,
            current_reps=5,
            quality=5  # Perfect
        )
        
        _, _, ef4, _ = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=1440,
            current_ef=2.5,
            current_reps=5,
            quality=4  # Good
        )
        
        assert ef5 > ef4
        assert ef5 > 2.5
    
    def test_ef_never_below_minimum(self):
        """EF should never go below MIN_EASINESS_FACTOR."""
        status, interval, ef, reps = SrsEngine.calculate_next_state(
            current_status='reviewing',
            current_interval=1440,
            current_ef=1.4,  # Close to minimum
            current_reps=5,
            quality=1  # Fail
        )
        
        assert ef >= SrsConstants.MIN_EASINESS_FACTOR


class TestSrsEngineLearningIntervals:
    """Test learning interval progression."""
    
    def test_first_rep_interval(self):
        interval = SrsEngine.get_learning_interval(1)
        assert interval == SrsConstants.LEARNING_STEPS_MINUTES[0]
    
    def test_intervals_match_steps(self):
        for i, expected in enumerate(SrsConstants.LEARNING_STEPS_MINUTES, 1):
            interval = SrsEngine.get_learning_interval(i)
            assert interval == expected
    
    def test_beyond_steps_uses_last(self):
        """Repetitions beyond defined steps should use last step interval."""
        interval = SrsEngine.get_learning_interval(100)
        assert interval == SrsConstants.LEARNING_STEPS_MINUTES[-1]


class TestSrsEngineShouldGraduate:
    """Test graduation from learning to reviewing."""
    
    def test_graduates_with_7_reps_quality_4(self):
        assert SrsEngine.should_graduate(7, 4) is True
    
    def test_graduates_with_8_reps_quality_5(self):
        assert SrsEngine.should_graduate(8, 5) is True
    
    def test_not_graduate_low_reps(self):
        assert SrsEngine.should_graduate(5, 5) is False
    
    def test_not_graduate_low_quality(self):
        assert SrsEngine.should_graduate(7, 3) is False


class TestSrsEngineNormalizeQuality:
    """Test quality normalization for different learning modes."""
    
    def test_flashcard_direct_quality(self):
        quality = SrsEngine.normalize_quality('flashcard', {'quality': 5})
        assert quality == 5
    
    def test_flashcard_rating_map(self):
        assert SrsEngine.normalize_quality('flashcard', {'rating': 'easy'}) == 5
        assert SrsEngine.normalize_quality('flashcard', {'rating': 'good'}) == 4
        assert SrsEngine.normalize_quality('flashcard', {'rating': 'hard'}) == 3
        assert SrsEngine.normalize_quality('flashcard', {'rating': 'again'}) == 1
    
    def test_mcq_correct(self):
        quality = SrsEngine.normalize_quality('mcq', {'is_correct': True})
        assert quality == 4
    
    def test_mcq_incorrect(self):
        quality = SrsEngine.normalize_quality('mcq', {'is_correct': False})
        assert quality == 1
    
    def test_quiz_correct(self):
        quality = SrsEngine.normalize_quality('quiz', {'correct': True})
        assert quality == 4
    
    def test_typing_perfect(self):
        quality = SrsEngine.normalize_quality('typing', {'accuracy': 1.0})
        assert quality == 5
    
    def test_typing_good(self):
        quality = SrsEngine.normalize_quality('typing', {'accuracy': 0.9})
        assert quality == 4
    
    def test_typing_fail(self):
        quality = SrsEngine.normalize_quality('typing', {'accuracy': 0.5})
        assert quality == 1
    
    def test_listening_same_as_typing(self):
        quality = SrsEngine.normalize_quality('listening', {'accuracy': 1.0})
        assert quality == 5


class TestSrsEngineRetention:
    """Test retention/forgetting curve calculations."""
    
    def test_retention_at_due_time_approximately_90(self):
        """Retention should be ~90% at exactly the due time."""
        interval = 1440  # 1 day in minutes
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        now = last_reviewed + datetime.timedelta(minutes=interval)
        
        retention = SrsEngine.calculate_retention(last_reviewed, interval, now)
        
        assert 0.88 < retention < 0.92
    
    def test_retention_before_due_higher_than_90(self):
        """Retention should be > 90% before due time."""
        interval = 1440
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        now = last_reviewed + datetime.timedelta(minutes=interval // 2)
        
        retention = SrsEngine.calculate_retention(last_reviewed, interval, now)
        
        assert retention > 0.9
    
    def test_retention_after_due_lower_than_90(self):
        """Retention should be < 90% after due time."""
        interval = 1440
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        now = last_reviewed + datetime.timedelta(minutes=interval * 2)
        
        retention = SrsEngine.calculate_retention(last_reviewed, interval, now)
        
        assert retention < 0.9
    
    def test_retention_max_100(self):
        """Retention should not exceed 1.0."""
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        retention = SrsEngine.calculate_retention(last_reviewed, 1440, last_reviewed)
        
        assert retention <= 1.0
    
    def test_retention_min_0(self):
        """Retention should not go below 0."""
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        now = last_reviewed + datetime.timedelta(days=365)  # 1 year later
        
        retention = SrsEngine.calculate_retention(last_reviewed, 1, now)
        
        assert retention >= 0.0
    
    def test_retention_none_last_reviewed(self):
        """Should return 0 if last_reviewed is None."""
        retention = SrsEngine.calculate_retention(None, 1440)
        assert retention == 0.0
    
    def test_retention_zero_interval(self):
        """Should return 0 if interval is 0 or negative."""
        last_reviewed = datetime.datetime.now(datetime.timezone.utc)
        assert SrsEngine.calculate_retention(last_reviewed, 0) == 0.0
        assert SrsEngine.calculate_retention(last_reviewed, -1) == 0.0


class TestSrsEngineUtilities:
    """Test utility methods."""
    
    def test_quality_to_description(self):
        assert SrsEngine.quality_to_description(0) == "Complete Fail"
        assert SrsEngine.quality_to_description(5) == "Perfect / Easy"
    
    def test_is_correct_threshold(self):
        assert SrsEngine.is_correct(3) is True
        assert SrsEngine.is_correct(2) is False
        assert SrsEngine.is_correct(5) is True

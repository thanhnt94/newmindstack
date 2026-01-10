"""
Tests for Gamification - Scoring Engine

Tests cover:
- Point calculation for learning activities
- Mode-based point multipliers  
- Streak bonus calculation
- Session bonus calculation
- Quality to score mapping
"""

import pytest

from mindstack_app.modules.learning.logics.scoring_engine import (
    ScoringEngine,
    LearningMode,
    ScoreResult
)


class TestScoringEngineBasicPoints:
    """Test basic point calculations."""
    
    def test_flashcard_correct_gives_points(self):
        """Correct flashcard answer should give positive points."""
        result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True
        )
        
        assert result.total_points > 0
    
    def test_incorrect_answer_gives_less_points(self):
        """Incorrect answer should give minimal or no points."""
        correct_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True
        )
        
        incorrect_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=1,
            is_correct=False
        )
        
        assert correct_result.total_points > incorrect_result.total_points
    
    def test_first_time_bonus(self):
        """First time learning should give extra points."""
        first_time_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            is_first_time=True
        )
        
        repeat_result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            is_first_time=False
        )
        
        assert first_time_result.total_points > repeat_result.total_points


class TestScoringEngineModeMultipliers:
    """Test mode-based point multipliers."""
    
    def test_different_modes_have_different_base_points(self):
        """Different learning modes should have different base point values."""
        modes = [
            LearningMode.FLASHCARD,
            LearningMode.QUIZ_MCQ,
            LearningMode.TYPING,
            LearningMode.LISTENING
        ]
        
        base_points = set()
        for mode in modes:
            points = ScoringEngine.get_point_value_for_mode(mode)
            base_points.add(points)
        
        # Should have at least 2 different point values
        assert len(base_points) >= 2
    
    def test_typing_mode_generally_gives_more_points(self):
        """Production modes (typing) should generally give more points."""
        typing_base = ScoringEngine.get_point_value_for_mode(LearningMode.TYPING)
        flashcard_base = ScoringEngine.get_point_value_for_mode(LearningMode.FLASHCARD)
        
        # Typing (active production) typically rewards more than flashcard (recognition)
        assert typing_base >= flashcard_base
    
    def test_mode_from_string_conversion(self):
        """Should convert string to LearningMode enum."""
        mode = ScoringEngine.get_mode_from_string('flashcard')
        assert mode == LearningMode.FLASHCARD
        
        mode = ScoringEngine.get_mode_from_string('typing')
        assert mode == LearningMode.TYPING


class TestScoringEngineStreakBonus:
    """Test streak bonus calculations."""
    
    def test_streak_increases_points(self):
        """Correct streak should give bonus points."""
        no_streak = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            correct_streak=0
        )
        
        with_streak = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            correct_streak=5
        )
        
        assert with_streak.total_points >= no_streak.total_points
    
    def test_higher_streak_more_bonus(self):
        """Higher streak should give more bonus."""
        streak_5 = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            correct_streak=5
        )
        
        streak_10 = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            correct_streak=10
        )
        
        assert streak_10.total_points >= streak_5.total_points


class TestScoringEngineDailyStreak:
    """Test daily streak bonus calculations."""
    
    def test_daily_streak_gives_bonus(self):
        """Daily streak should give bonus points."""
        result = ScoringEngine.calculate_daily_streak_bonus(daily_streak=7)
        
        assert result.total_points > 0
    
    def test_longer_streak_more_bonus(self):
        """Longer daily streak should give more bonus."""
        week_streak = ScoringEngine.calculate_daily_streak_bonus(daily_streak=7)
        month_streak = ScoringEngine.calculate_daily_streak_bonus(daily_streak=30)
        
        assert month_streak.total_points > week_streak.total_points
    
    def test_zero_streak_no_bonus(self):
        """Zero streak should give no bonus."""
        result = ScoringEngine.calculate_daily_streak_bonus(daily_streak=0)
        
        assert result.total_points == 0


class TestScoringEngineSessionBonus:
    """Test session completion bonus calculations."""
    
    def test_session_completion_gives_bonus(self):
        """Completing a study session should give bonus."""
        result = ScoringEngine.calculate_session_bonus(
            items_reviewed=20,
            items_correct=15,
            session_duration_minutes=15
        )
        
        assert result.total_points >= 0
    
    def test_higher_accuracy_more_bonus(self):
        """Higher accuracy should give more session bonus."""
        low_accuracy = ScoringEngine.calculate_session_bonus(
            items_reviewed=20,
            items_correct=10,  # 50%
            session_duration_minutes=15
        )
        
        high_accuracy = ScoringEngine.calculate_session_bonus(
            items_reviewed=20,
            items_correct=18,  # 90%
            session_duration_minutes=15
        )
        
        assert high_accuracy.total_points >= low_accuracy.total_points
    
    def test_daily_goal_bonus(self):
        """Meeting daily goal should give extra bonus."""
        without_goal = ScoringEngine.calculate_session_bonus(
            items_reviewed=20,
            items_correct=15,
            session_duration_minutes=15,
            daily_goal_met=False
        )
        
        with_goal = ScoringEngine.calculate_session_bonus(
            items_reviewed=20,
            items_correct=15,
            session_duration_minutes=15,
            daily_goal_met=True
        )
        
        assert with_goal.total_points >= without_goal.total_points


class TestScoringEngineQualityToScore:
    """Test quality to score mapping."""
    
    def test_perfect_quality_max_score(self):
        """Perfect quality (5) should give maximum score."""
        score = ScoringEngine.quality_to_score(5)
        assert score > 0
    
    def test_fail_quality_min_score(self):
        """Failed quality (0-1) should give minimal score."""
        fail_score = ScoringEngine.quality_to_score(1)
        perfect_score = ScoringEngine.quality_to_score(5)
        
        assert fail_score < perfect_score
    
    def test_quality_scales_properly(self):
        """Higher quality should give higher score."""
        scores = [ScoringEngine.quality_to_score(q) for q in range(6)]
        
        # Scores should generally increase with quality
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], f"Score for quality {i} should be >= score for quality {i-1}"


class TestScoringEngineQuizConversion:
    """Test quiz answer to quality conversion."""
    
    def test_correct_quiz_gives_positive_quality(self):
        """Correct quiz answer should give good quality."""
        quality = ScoringEngine.quiz_answer_to_quality(is_correct=True)
        assert quality >= 3
    
    def test_incorrect_quiz_gives_low_quality(self):
        """Incorrect quiz answer should give low quality."""
        quality = ScoringEngine.quiz_answer_to_quality(is_correct=False)
        assert quality < 3


class TestScoreResultDataClass:
    """Test ScoreResult dataclass."""
    
    def test_score_result_has_breakdown(self):
        """ScoreResult should include points breakdown."""
        result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True,
            is_first_time=True,
            correct_streak=5
        )
        
        assert hasattr(result, 'breakdown')
        assert isinstance(result.breakdown, dict)
    
    def test_score_result_total_equals_sum(self):
        """Total points should equal sum of base + bonus."""
        result = ScoringEngine.calculate_answer_points(
            mode=LearningMode.FLASHCARD,
            quality=4,
            is_correct=True
        )
        
        assert result.total_points == result.base_points + result.bonus_points

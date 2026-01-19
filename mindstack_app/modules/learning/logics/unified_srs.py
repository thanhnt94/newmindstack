"""
Unified SRS System - Hybrid SM-2 + Memory Power

This module provides a unified interface for all learning modes, combining:
- SM-2 Algorithm for scheduling and interval calculation
- Memory Power metrics for user-facing analytics

All learning modes (flashcard, quiz, typing, listening, etc.) use this
single entry point for consistency and maintainability.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .srs_engine import SrsEngine
from .memory_engine import MemoryEngine
from .scoring_engine import ScoringEngine


@dataclass
class SrsResult:
    """Result of processing a learning interaction."""
    # Scheduling results
    next_review: datetime
    interval_minutes: int
    status: str  # 'new', 'learning', 'reviewing'
    
    # Memory Power analytics
    mastery: float  # 0.0-1.0
    retention: float  # 0.0-1.0
    memory_power: float  # mastery × retention
    
    # Streaks
    correct_streak: int
    incorrect_streak: int
    
    # Scoring
    score_points: int
    score_breakdown: Dict[str, int]
    
    # Internal State (for persistence)
    repetitions: int
    easiness_factor: float
    
    # Spec v8 fields
    custom_state: str = 'new'
    hard_streak: int = 0
    learning_reps: int = 0
    precise_interval: float = 20.0


class UnifiedSrsSystem:
    """
    Unified SRS System combining SM-2 and Memory Power.
    
    This class orchestrates:
    - SM-2 for interval calculation (backend scheduling)
    - Memory Power for user metrics (frontend display)
    - Quality normalization across different learning modes
    
    Usage:
        result = UnifiedSrsSystem.process_answer(
            user_id=1,
            item_id=42,
            quality=4,
            mode='flashcard'
        )
    """
    
    # === MAIN ENTRY POINT ===
    
    @staticmethod
    def process_answer(
        # Current state
        current_status: str,
        current_interval: int,
        current_ef: float,
        current_reps: int,
        current_correct_streak: int,
        current_incorrect_streak: int,
        last_reviewed: Optional[datetime],
        
        # Answer quality
        quality: int,  # 0-7
        mode: str,  # Learning mode
        
        # Additional context
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None,
        
        # Spec v8 fields
        custom_state: str = 'new',
        hard_streak: int = 0,
        learning_reps: int = 0,
        precise_interval: float = 20.0
    ) -> SrsResult:
        """
        Process a learning answer using Spec v8 Custom SRS + Memory Power.
        """
        from .memory_engine import ProgressState
        
        now = datetime.now(timezone.utc)
        is_correct = quality >= 3
        
        # === 1. BUILD INPUT STATE ===
        state_input = ProgressState(
            status=current_status,
            mastery=0.0,
            repetitions=current_reps,
            interval=current_interval,
            correct_streak=current_correct_streak,
            incorrect_streak=current_incorrect_streak,
            easiness_factor=current_ef,
            custom_state=custom_state,
            hard_streak=hard_streak,
            learning_reps=learning_reps,
            precise_interval=precise_interval
        )
        
        # Inject last_reviewed for Review Ahead logic
        state_input.last_reviewed = last_reviewed
        
        # === 2. PROCESS WITH SPEC v7 ENGINE ===
        engine_result = MemoryEngine.process_answer(
            current_state=state_input,
            quality=quality,
            now=now
        )
        
        new_state = engine_result.new_state
        
        # Calculate due time
        next_review = now + timedelta(minutes=new_state.interval)
        
        # === 3. SCORING ===
        score_result = ScoringEngine.calculate_answer_points(
            mode=mode,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=new_state.correct_streak,
            response_time_seconds=response_time_seconds
        )
        
        # === 4. RETURN RESULTS ===
        return SrsResult(
            # Scheduling
            next_review=next_review,
            interval_minutes=new_state.interval,
            status=new_state.status,
            
            # Memory Power (retention = R0 from score at t=0)
            mastery=new_state.mastery,
            retention=engine_result.retention_percent / 100.0,
            memory_power=engine_result.memory_power,
            
            # Streaks
            correct_streak=new_state.correct_streak,
            incorrect_streak=new_state.incorrect_streak,
            
            # Scoring
            score_points=score_result.total_points,
            score_breakdown=score_result.breakdown,
            
            # Internal
            repetitions=new_state.repetitions,
            easiness_factor=new_state.easiness_factor,
            
            # Spec v8
            custom_state=new_state.custom_state,
            hard_streak=new_state.hard_streak,
            learning_reps=new_state.learning_reps,
            precise_interval=new_state.precise_interval
        )
    
    # === ANALYTICS HELPER ===
    
    @staticmethod
    def get_current_stats(
        status: str,
        repetitions: int,
        correct_streak: int,
        incorrect_streak: int,
        last_reviewed: Optional[datetime],
        interval: int,
        due_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate real-time Memory Power stats for display.
        
        This is called when displaying dashboard or item details.
        Mastery is calculated from stored data, retention decays over time.
        
        Args:
            status: Learning status
            repetitions: Total reps
            correct_streak: Consecutive correct
            incorrect_streak: Consecutive incorrect
            last_reviewed: Last review timestamp
            interval: Current interval in minutes
            due_time: When due for next review
        
        Returns:
            Dict with mastery, retention, memory_power, is_due
        """
        # Calculate mastery (stable, doesn't change without interaction)
        mastery = MemoryEngine.calculate_mastery(
            status=status,
            repetitions=repetitions,
            correct_streak=correct_streak,
            incorrect_streak=incorrect_streak
        )
        
        # Calculate retention (decays over time - real-time calculation)
        now = datetime.now(timezone.utc)
        retention = MemoryEngine.calculate_retention(
            last_reviewed=last_reviewed,
            interval=interval,
            now=now
        )
        
        # Current memory power
        memory_power = MemoryEngine.calculate_memory_power(mastery, retention)
        
        # Check if due (fix timezone awareness)
        if due_time:
            due_aware = due_time.replace(tzinfo=timezone.utc) if due_time.tzinfo is None else due_time
            is_due = now >= due_aware
        else:
            is_due = True
        
        return {
            'mastery': mastery,
            'retention': retention,
            'memory_power': memory_power,
            'is_due': is_due,
            'status': status
        }
    
    # === QUALITY NORMALIZATION ===
    
    @staticmethod
    def normalize_quality(mode: str, result_data: Dict[str, Any]) -> int:
        """
        Normalize mode-specific results to SM-2 quality (0-5).
        
        This is a convenience wrapper around SrsEngine.normalize_quality().
        
        Args:
            mode: Learning mode
            result_data: Mode-specific result data
        
        Returns:
            Normalized quality (0-5)
        """
        return SrsEngine.normalize_quality(mode, result_data)
    
    # === BATCH OPERATIONS ===
    
    @staticmethod
    def calculate_batch_stats(
        progress_records: list,
        now: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for multiple items efficiently.
        
        Used for dashboard analytics.
        
        Args:
            progress_records: List of LearningProgress objects
            now: Current time (default: now)
        
        Returns:
            Aggregate stats dictionary
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        stats_list = []
        
        for progress in progress_records:
            # Calculate mastery
            mastery = MemoryEngine.calculate_mastery(
                status=progress.status,
                repetitions=progress.repetitions,
                correct_streak=progress.correct_streak,
                incorrect_streak=progress.incorrect_streak
            )
            
            # Calculate retention
            retention = MemoryEngine.calculate_retention(
                last_reviewed=progress.last_reviewed,
                interval=progress.interval,
                now=now
            )
            
            memory_power = mastery * retention
            # Fix: make due_time aware before comparison
            if progress.due_time:
                due_aware = progress.due_time.replace(tzinfo=timezone.utc) if progress.due_time.tzinfo is None else progress.due_time
                is_due = now >= due_aware
            else:
                is_due = True
            
            stats_list.append({
                'item_id': progress.item_id,
                'memory_power': memory_power,
                'mastery': mastery,
                'retention': retention,
                'is_due': is_due
            })
        
        # Aggregate
        total_items = len(stats_list)
        if total_items == 0:
            return {
                'total_items': 0,
                'average_memory_power': 0,
                'strong_items': 0,
                'medium_items': 0,
                'weak_items': 0,
                'due_items': 0
            }
        
        avg_mp = sum(s['memory_power'] for s in stats_list) / total_items
        strong = len([s for s in stats_list if s['memory_power'] >= 0.8])
        medium = len([s for s in stats_list if 0.5 <= s['memory_power'] < 0.8])
        weak = len([s for s in stats_list if s['memory_power'] < 0.5])
        due = len([s for s in stats_list if s['is_due']])
        
        return {
            'total_items': total_items,
            'average_memory_power': round(avg_mp, 4),
            'strong_items': strong,  # 80-100%
            'medium_items': medium,  # 50-80%
            'weak_items': weak,  # 0-50%
            'due_items': due
        }

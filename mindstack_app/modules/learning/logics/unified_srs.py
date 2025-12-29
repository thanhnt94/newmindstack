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
    # SM-2 scheduling results
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
        quality: int,  # 0-5
        mode: str,  # Learning mode
        
        # Additional context
        is_first_time: bool = False,
        response_time_seconds: Optional[float] = None
    ) -> SrsResult:
        """
        Process a learning answer using hybrid SM-2 + Memory Power.
        
        Args:
            current_status: Current learning status ('new', 'learning', 'reviewing')
            current_interval: Current interval in minutes
            current_ef: Current easiness factor
            current_reps: Current repetition count
            current_correct_streak: Current consecutive correct answers
            current_incorrect_streak: Current consecutive incorrect answers
            last_reviewed: When last reviewed (None if never)
            quality: Answer quality (0-5)
            mode: Learning mode ('flashcard', 'quiz_mcq', 'typing', etc.)
            is_first_time: Whether this is first time seeing this item
            response_time_seconds: Time taken to answer (for speed bonus)
        
        Returns:
            SrsResult with scheduling and analytics data
        """
        is_correct = quality >= 3
        
        # === 1. SM-2 CALCULATION (Backend - Scheduling) ===
        new_status, new_interval, new_ef, new_reps = SrsEngine.calculate_next_state(
            current_status=current_status,
            current_interval=current_interval,
            current_ef=current_ef,
            current_reps=current_reps,
            quality=quality
        )
        
        # Calculate due time
        now = datetime.now(timezone.utc)
        next_review = now + timedelta(minutes=new_interval)
        
        # === 2. UPDATE STREAKS ===
        if is_correct:
            new_correct_streak = current_correct_streak + 1
            new_incorrect_streak = 0
        else:
            new_correct_streak = 0
            new_incorrect_streak = current_incorrect_streak + 1
        
        # === 3. MEMORY POWER CALCULATION (Frontend - Analytics) ===
        # Calculate mastery based on new state
        mastery = MemoryEngine.calculate_mastery(
            status=new_status,
            repetitions=new_reps,
            correct_streak=new_correct_streak,
            incorrect_streak=new_incorrect_streak
        )
        
        # Retention is 100% immediately after answering
        retention = 1.0
        
        # Memory power
        memory_power = MemoryEngine.calculate_memory_power(mastery, retention)
        
        # === 4. SCORING ===
        score_result = ScoringEngine.calculate_answer_points(
            mode=mode,
            quality=quality,
            is_correct=is_correct,
            is_first_time=is_first_time,
            correct_streak=new_correct_streak,
            response_time_seconds=response_time_seconds
        )
        
        # === 5. RETURN RESULTS ===
        return SrsResult(
            # SM-2 scheduling
            next_review=next_review,
            interval_minutes=new_interval,
            status=new_status,
            
            # Memory Power metrics
            mastery=mastery,
            retention=retention,
            memory_power=memory_power,
            
            # Streaks
            correct_streak=new_correct_streak,
            incorrect_streak=new_incorrect_streak,
            
            # Scoring
            score_points=score_result.total_points,
            score_breakdown=score_result.breakdown
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

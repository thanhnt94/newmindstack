# File: vocabulary/stats/session_stats.py
# Vocabulary Session Statistics
# Tracks statistics during an active learning session (MCQ, flashcard, etc.)

from datetime import datetime
from typing import Optional, List, Dict


class VocabularySessionStats:
    """
    In-session statistics tracker for vocabulary learning.
    Use this to track progress during MCQ, flashcard, or other learning sessions.
    """
    
    def __init__(self, user_id: int, container_id: int, mode: str, total_items: int = 0):
        """
        Initialize a new session stats tracker.
        
        Args:
            user_id: The user's ID
            container_id: The vocabulary container ID
            mode: Learning mode ('mcq', 'flashcard', 'typing', 'matching', etc.)
            total_items: Expected total items in session
        """
        self.user_id = user_id
        self.container_id = container_id
        self.mode = mode
        self.total_items = total_items
        self.started_at = datetime.utcnow()
        self.ended_at: Optional[datetime] = None
        
        # Answer tracking
        self.answers: List[Dict] = []
        self.correct_count = 0
        self.incorrect_count = 0
        self.current_streak = 0
        self.best_streak = 0
        
    def record_answer(self, item_id: int, is_correct: bool, time_ms: int = 0, 
                      extra_data: Optional[Dict] = None) -> Dict:
        """
        Record an answer during the session.
        
        Args:
            item_id: The item ID that was answered
            is_correct: Whether the answer was correct
            time_ms: Time taken to answer in milliseconds
            extra_data: Optional additional data to store
            
        Returns:
            Current session stats after recording
        """
        answer = {
            'item_id': item_id,
            'is_correct': is_correct,
            'time_ms': time_ms,
            'timestamp': datetime.utcnow().isoformat(),
            'extra': extra_data or {}
        }
        self.answers.append(answer)
        
        if is_correct:
            self.correct_count += 1
            self.current_streak += 1
            if self.current_streak > self.best_streak:
                self.best_streak = self.current_streak
        else:
            self.incorrect_count += 1
            self.current_streak = 0
        
        return self.get_current_stats()
    
    def get_current_stats(self) -> Dict:
        """
        Get current session statistics.
        
        Returns:
            Dict with current session stats
        """
        total_answered = len(self.answers)
        accuracy_pct = (self.correct_count / total_answered * 100) if total_answered > 0 else 0
        avg_time_ms = sum(a['time_ms'] for a in self.answers) / total_answered if total_answered > 0 else 0
        
        elapsed = datetime.utcnow() - self.started_at
        elapsed_seconds = int(elapsed.total_seconds())
        
        remaining = self.total_items - total_answered if self.total_items > 0 else 0
        progress_pct = (total_answered / self.total_items * 100) if self.total_items > 0 else 0
        
        return {
            # Progress
            'total_items': self.total_items,
            'total_answered': total_answered,
            'remaining': remaining,
            'progress_pct': round(progress_pct, 1),
            
            # Accuracy
            'correct': self.correct_count,
            'incorrect': self.incorrect_count,
            'accuracy_pct': round(accuracy_pct, 1),
            
            # Streaks
            'current_streak': self.current_streak,
            'best_streak': self.best_streak,
            
            # Time
            'avg_time_ms': int(avg_time_ms),
            'elapsed_seconds': elapsed_seconds,
            
            # Session info
            'mode': self.mode,
            'is_complete': total_answered >= self.total_items if self.total_items > 0 else False
        }
    
    def finalize(self) -> Dict:
        """
        End the session and return final statistics.
        
        Returns:
            Dict with final session stats including summary
        """
        self.ended_at = datetime.utcnow()
        
        stats = self.get_current_stats()
        stats['ended_at'] = self.ended_at.isoformat()
        stats['started_at'] = self.started_at.isoformat()
        
        duration = self.ended_at - self.started_at
        stats['duration_seconds'] = int(duration.total_seconds())
        
        # Add answer history summary
        stats['answers'] = self.answers
        
        return stats
    
    def to_dict(self) -> Dict:
        """Serialize session to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'container_id': self.container_id,
            'mode': self.mode,
            'total_items': self.total_items,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'stats': self.get_current_stats(),
            'answers': self.answers
        }

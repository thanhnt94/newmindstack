
import unittest
from datetime import datetime, timedelta, timezone
from mindstack_app.modules.learning.core.logics.memory_engine import MemoryEngine, ProgressState

class TestMemoryEngine(unittest.TestCase):

    def setUp(self):
        self.now = datetime.now(timezone.utc)

    # === MASTERY TESTS ===

    def test_mastery_new(self):
        """New items should have 0 mastery."""
        m = MemoryEngine.calculate_mastery('new', 0, 0, 0)
        self.assertEqual(m, 0.0)

    def test_mastery_learning_growth(self):
        """Learning items should grow from 0.10 to ~0.52 over 7 reps."""
        # Rep 1
        m1 = MemoryEngine.calculate_mastery('learning', 1, 1, 0)
        self.assertEqual(m1, 0.16) # 0.10 + 0.06
        
        # Rep 7 (Check max)
        m7 = MemoryEngine.calculate_mastery('learning', 7, 7, 0)
        self.assertEqual(m7, 0.52) # 0.10 + 7*0.06 = 0.52

    def test_mastery_reviewing_growth(self):
        """Reviewing items start at 0.60."""
        # Rep 0 (just graduated)
        m = MemoryEngine.calculate_mastery('reviewing', 0, 0, 0)
        self.assertEqual(m, 0.60) # Base reviewing
        
        # Rep 5
        m5 = MemoryEngine.calculate_mastery('reviewing', 5, 5, 0)
        # Base 0.60 + 5*0.057 = 0.60 + 0.285 = 0.885
        # Streak (5-5)*0.02 = 0
        self.assertEqual(m5, 0.885)

    def test_correct_streak_bonus(self):
        """Long streaks give bonus mastery."""
        # Reviewing, 10 streak
        # Base: 0.60 + 7*0.057 (max reps) = 0.999... wait
        # 0.60 + 0.399 = 0.999
        # Streak bonus: (10-5)*0.02 = 0.10
        # Total > 1.0, should be capped
        m = MemoryEngine.calculate_mastery('reviewing', 20, 10, 0)
        self.assertEqual(m, 1.0)
        
        # Smaller streak bonus test
        # Reps 0, Streak 6 (unlikely but logic test)
        # Base 0.60
        # Bonus (6-5)*0.02 = 0.02
        m = MemoryEngine.calculate_mastery('reviewing', 0, 6, 0)
        self.assertEqual(m, 0.62)

    def test_incorrect_streak_penalty(self):
        """Incorrect answers reduce mastery."""
        # High mastery penalty
        # Base mastery for reviewing rep 5 = 0.885
        # 1 Wrong
        # penalty = min(1 * 0.15, 0.885 - 0.10) => 0.15
        # result = 0.885 - 0.15 = 0.735
        m = MemoryEngine.calculate_mastery('reviewing', 5, 0, 1)
        self.assertEqual(m, 0.735)

    # === RETENTION TESTS ===

    def test_retention_fresh(self):
        """Just reviewed item has 100% retention."""
        r = MemoryEngine.calculate_retention(self.now, 60, self.now)
        self.assertEqual(r, 1.0)

    def test_retention_at_interval(self):
        """At exactly the interval time, retention should be ~90%."""
        interval_mins = 100
        reviewed_at = self.now - timedelta(minutes=interval_mins)
        
        r = MemoryEngine.calculate_retention(reviewed_at, interval_mins, self.now)
        
        # decay_rate = 0.105 / 100
        # elapsed = 100
        # exponent = -0.105
        # e^-0.105 ≈ 0.9003
        self.assertAlmostEqual(r, 0.900, places=3)

    def test_retention_decay(self):
        """Retention drops over time."""
        interval = 60
        
        r1 = MemoryEngine.calculate_retention(self.now - timedelta(minutes=30), interval, self.now)
        r2 = MemoryEngine.calculate_retention(self.now - timedelta(minutes=60), interval, self.now) # ~0.90
        r3 = MemoryEngine.calculate_retention(self.now - timedelta(minutes=120), interval, self.now)
        
        self.assertGreater(r1, r2)
        self.assertGreater(r2, r3)

    # === PROCESS ANSWER TESTS ===

    def test_answer_new_correct(self):
        """New item correct answer -> Learning."""
        state = ProgressState('new', 0.0, 0, 0, 0, 0, 2.5)
        
        res = MemoryEngine.process_answer(state, 5, self.now)
        
        self.assertEqual(res.new_state.status, 'learning')
        self.assertEqual(res.new_state.repetitions, 1)
        self.assertEqual(res.new_state.correct_streak, 1)
        self.assertGreater(res.new_state.mastery, 0.0)

    def test_answer_reviewing_incorrect_hard_reset(self):
        """3 incorrects in reviewing -> Reset to Learning."""
        # Already has 2 incorrects
        state = ProgressState('reviewing', 0.5, 10, 1440, 0, 2, 2.5)
        
        res = MemoryEngine.process_answer(state, 1, self.now) # Another wrong -> total 3
        
        self.assertEqual(res.new_state.status, 'learning') # Reset
        self.assertEqual(res.new_state.repetitions, 0)
        self.assertEqual(res.new_state.mastery, 0.10) # Floor
        self.assertEqual(res.new_state.interval, 10) # Relearning interval

if __name__ == '__main__':
    unittest.main()

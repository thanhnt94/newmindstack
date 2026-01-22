import statistics
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List

# Mock the CardState and HybridFSRSEngine for standalone testing
@dataclass
class CardState:
    stability: float = 0.0
    difficulty: float = 0.0
    elapsed_days: float = 0.0
    scheduled_days: float = 0
    reps: int = 0
    lapses: int = 0
    state: int = 2 # Review
    last_review: Optional[datetime] = None
    due: Optional[datetime] = None

class Rating:
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

# Simplified logic from hybrid_fsrs.py
def apply_fuzz(final_interval: float) -> float:
    if final_interval > 3.0:
        import random as py_random
        # Use a fixed seed for reproducibility in this specific test if needed, 
        # but here we want to see variance.
        fuzz_factor = py_random.uniform(0.95, 1.05)
        fuzzed_interval = final_interval * fuzz_factor
        return max(3.0, fuzzed_interval)
    return final_interval

def test_fuzzing():
    print("Testing FSRS Interval Fuzzing...")
    
    test_intervals = [1.0, 5.0, 30.0, 100.0]
    iterations = 100
    
    for base in test_intervals:
        results = [apply_fuzz(base) for _ in range(iterations)]
        
        min_val = min(results)
        max_val = max(results)
        std_dev = statistics.stdev(results) if len(results) > 1 else 0
        
        print(f"\nBase Interval: {base} days")
        print(f"  Min: {min_val:.4f}, Max: {max_val:.4f}")
        print(f"  Range: {max_val - min_val:.4f}")
        print(f"  StdDev: {std_dev:.4f}")
        
        if base <= 3.0:
            if std_dev == 0:
                print("  [PASS] No fuzzing applied below threshold.")
            else:
                print("  [FAIL] Fuzzing applied below threshold!")
        else:
            if std_dev > 0:
                # 10% total range means std_dev should be around 0.02-0.03 * base
                expected_min_std = 0.01 * base
                if std_dev >= expected_min_std:
                     print(f"  [PASS] Fuzzing detected (StdDev {std_dev:.4f} >= {expected_min_std:.4f})")
                else:
                     print(f"  [FAIL] Fuzzing too weak or not detected.")
            else:
                print("  [FAIL] No fuzzing detected for mature interval!")

if __name__ == "__main__":
    test_fuzzing()

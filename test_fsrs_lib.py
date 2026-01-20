"""
Test script for fsrs-rs-python library.
Verifies basic FSRS functionality with the new Rust-based library.
"""
from fsrs_rs_python import FSRS, DEFAULT_PARAMETERS
import datetime

def test_fsrs():
    # Initialize FSRS with default parameters
    f = FSRS(parameters=list(DEFAULT_PARAMETERS))
    
    # Test: New card review
    # next_states(memory_state, desired_retention, days_elapsed)
    # memory_state=None means new card
    result = f.next_states(None, 0.9, 0)
    
    print("=== New Card Next States (retention=0.9) ===")
    print(f"Again: interval={result.again.interval:.4f}d, stability={result.again.memory.stability:.4f}")
    print(f"Hard:  interval={result.hard.interval:.4f}d, stability={result.hard.memory.stability:.4f}")
    print(f"Good:  interval={result.good.interval:.4f}d, stability={result.good.memory.stability:.4f}")
    print(f"Easy:  interval={result.easy.interval:.4f}d, stability={result.easy.memory.stability:.4f}")
    
    # Test: Review after learning (simulate Good answer)
    good_memory = result.good.memory
    print(f"\n=== After Good Review (S={good_memory.stability:.4f}, D={good_memory.difficulty:.4f}) ===")
    
    # Simulate 1 day elapsed (must be int)
    result2 = f.next_states(good_memory, 0.9, 1)
    print(f"Again: interval={result2.again.interval:.4f}d")
    print(f"Good:  interval={result2.good.interval:.4f}d")
    print(f"Easy:  interval={result2.easy.interval:.4f}d")
    
    # Test with different retention
    print("\n=== Different Retention Targets ===")
    for ret in [0.85, 0.90, 0.95]:
        r = f.next_states(None, ret, 0)
        print(f"Retention {ret}: Good interval = {r.good.interval:.4f}d")

if __name__ == "__main__":
    try:
        test_fsrs()
        print("\n✓ fsrs-rs-python is working correctly!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n✗ Error: {e}")

from datetime import datetime, timedelta
import random as py_random

class Rating:
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

def simulate_load_balancer(due_count, daily_limit, rating, original_due):
    next_due = original_due
    
    # Logic from fsrs_service.py
    if due_count > daily_limit and rating >= Rating.Good:
        shift = py_random.choice([-1, 1])
        next_due = next_due + timedelta(days=shift)
        return next_due, shift
    
    return next_due, 0

def test_load_balancing():
    print("Testing FSRS Load Balancing Logic...")
    
    daily_limit = 200
    base_date = datetime(2026, 1, 1, 10, 0)
    
    test_cases = [
        # (Current Due Count, Limit, Rating, Expected Shifted?)
        (100, 200, Rating.Good, False),  # Under limit
        (250, 200, Rating.Again, False), # Over limit but critical (Again)
        (250, 200, Rating.Hard, False),  # Over limit but critical (Hard)
        (250, 200, Rating.Good, True),   # Over limit and flexible (Good)
        (250, 200, Rating.Easy, True),   # Over limit and flexible (Easy)
    ]
    
    all_passed = True
    for count, limit, rating, expected_shift in test_cases:
        actual_due, shift = simulate_load_balancer(count, limit, rating, base_date)
        
        has_shifted = (shift != 0)
        status = "PASS" if has_shifted == expected_shift else "FAIL"
        
        print(f"Count: {count}, Rating: {rating} -> Shifted: {has_shifted} (Shift: {shift}) [{status}]")
        if status == "FAIL":
            all_passed = False
            
    if all_passed:
        print("\nAll Load Balancing logic tests PASSED!")
    else:
        print("\nSome Load Balancing logic tests FAILED!")

if __name__ == "__main__":
    test_load_balancing()

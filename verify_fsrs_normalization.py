from typing import Any

def normalize_rating(quality: Any) -> int:
    """Mock of FsrsService._normalize_rating for verification."""
    if quality is None:
        return 1
    
    try:
        q = int(quality)
    except (ValueError, TypeError):
        return 1

    if q <= 1:
        return 1
    elif q == 2:
        return 2
    elif q == 3:
        return 3
    else:
        return 4

test_cases = [
    (None, 1),
    (0, 1),
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 4),
    (6, 4),
    ("1", 1),
    ("2", 2),
    ("abc", 1),
]

print("Verifying FSRS Rating Normalization...")
all_passed = True
for inp, expected in test_cases:
    result = normalize_rating(inp)
    status = "PASS" if result == expected else "FAIL"
    print(f"Input: {inp!r} -> Expected: {expected}, Got: {result} [{status}]")
    if result != expected:
        all_passed = False

if all_passed:
    print("\nAll test cases PASSED!")
else:
    print("\nSome test cases FAILED!")

from typing import Any

class Rating:
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

def calculate_quiz_rating(is_correct: bool, duration_ms: int) -> int:
    if not is_correct:
        return Rating.Again
    
    easy_threshold = 3000
    good_threshold = 10000
    
    if duration_ms < easy_threshold:
        return Rating.Easy
    elif duration_ms <= good_threshold:
        return Rating.Good
    else:
        return Rating.Hard

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def calculate_typing_rating(target_text: str, user_answer: str, duration_ms: int) -> int:
    if not target_text or not user_answer:
        return Rating.Again
        
    t = target_text.strip().lower()
    u = user_answer.strip().lower()
    
    if t == u:
        if duration_ms > 0:
            wpm = (len(t) / 5.0) / (duration_ms / 60000.0)
            if wpm >= 40:
                return Rating.Easy
        return Rating.Good
        
    distance = levenshtein_distance(t, u)
    max_len = max(len(t), len(u), 1)
    similarity = 1.0 - (distance / max_len)
    
    if similarity >= 0.8:
        return Rating.Hard
        
    return Rating.Again

# Test Quiz
quiz_tests = [
    (False, 1000, Rating.Again),
    (True, 1000, Rating.Easy),
    (True, 5000, Rating.Good),
    (True, 15000, Rating.Hard),
]

# Test Typing
typing_tests = [
    ("hello", "hello", 1000, Rating.Easy), # 1 word, 1s -> 60 WPM
    ("hello", "hello", 5000, Rating.Good), # 1 word, 5s -> 12 WPM
    ("hello world", "hello word", 1000, Rating.Hard), # Minor typo
    ("hello world", "abc", 1000, Rating.Again), # Major error
]

print("Verifying Implicit Ratings...")
all_passed = True

print("\n--- Quiz Tests ---")
for is_correct, dur, expected in quiz_tests:
    res = calculate_quiz_rating(is_correct, dur)
    status = "PASS" if res == expected else "FAIL"
    print(f"Correct: {is_correct}, Duration: {dur} -> Expected: {expected}, Got: {res} [{status}]")
    if res != expected: all_passed = False

print("\n--- Typing Tests ---")
for target, user, dur, expected in typing_tests:
    res = calculate_typing_rating(target, user, dur)
    status = "PASS" if res == expected else "FAIL"
    print(f"Target: {target!r}, User: {user!r}, Dur: {dur} -> Expected: {expected}, Got: {res} [{status}]")
    if res != expected: all_passed = False

if all_passed:
    print("\nAll implicit rating tests PASSED!")
else:
    print("\nSome implicit rating tests FAILED!")

"""
Marker Logic
===========

Pure logic for evaluating academic correctness of answers.
This module handles:
- Text normalization (stripping, case-folding)
- Comparison logic (exact match, fuzziness)
- Grading calculations (pass/fail based on thresholds)

This module MUST be Pure Python and not depend on Database models.
"""

import difflib
import re

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Strip whitespace, lowercase
    text = text.strip().lower()
    # Normalize varied whitespace to single space
    text = re.sub(r'\s+', ' ', text)
    # Remove common punctuation for loose matching? (Optional, maybe configurable)
    return text

def compare_text(submission: str, solution: str, tolerance: float = 0.0) -> dict:
    """
    Compare submission against solution.
    
    Args:
        submission: User's answer
        solution: Correct answer
        tolerance: Fuzziness allowed (0.0 = exact match, 0.2 = allow 20% diff)
    
    Returns:
        dict: Evaluation result with keys:
            - is_correct (bool)
            - score (float 0.0-1.0)
            - diff (list)
            - ratio (float)
    """
    norm_sub = normalize_text(submission)
    norm_sol = normalize_text(solution)
    
    if not norm_sol:
        # Edge case: Empty solution?
        return {
            'is_correct': False,
            'score': 0.0,
            'reason': 'No solution provided'
        }

    # Algorithm: SequenceMatcher
    matcher = difflib.SequenceMatcher(None, norm_sub, norm_sol)
    ratio = matcher.ratio()
    
    # Check threshold (1.0 - tolerance)
    # e.g. tolerance 0.0 -> threshold 1.0 (Exact)
    # e.g. tolerance 0.2 -> threshold 0.8
    threshold = 1.0 - tolerance
    is_correct = ratio >= threshold
    
    # If submission is effectively empty but solution wasn't
    if not norm_sub and norm_sol:
        is_correct = False
        ratio = 0.0

    return {
        'is_correct': is_correct,
        'score': ratio,
        'ratio': ratio,
        'threshold': threshold,
        'diff': list(difflib.ndiff(norm_sub, norm_sol)) if not is_correct else []
    }

def evaluate_multiple_choice(submission: str, correct_option: str) -> dict:
    """Evaluate MCQ answer (A, B, C, D)."""
    is_correct = normalize_text(submission) == normalize_text(correct_option)
    return {
        'is_correct': is_correct,
        'score': 1.0 if is_correct else 0.0
    }

"""
Unit tests for SmartDistractorSelector.
Run: python -m pytest tests/test_smart_selector.py -v
"""

import sys
import os
import random

# Add project root to path so we can import the module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mindstack_app.modules.vocabulary.mcq.engine.selector import SmartDistractorSelector


class TestSmartDistractorSelector:
    """Test suite for the SmartDistractorSelector algorithm."""

    # ------------------------------------------------------------------ #
    #  Vietnamese (space-separated) tests                                  #
    # ------------------------------------------------------------------ #

    def test_vietnamese_prefers_word_overlap(self):
        """'con người' should prefer 'con chó' (shares 'con') over 'mèo'."""
        random.seed(42)
        correct = "con người"
        pool = ["con chó", "cái ghế", "người máy", "mèo"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=2)
        
        assert len(results) == 2
        # 'con chó' shares 'con' AND has same word count (2)
        # 'người máy' shares 'người' AND has same word count (2)
        # Both should be strongly preferred over 'cái ghế' and 'mèo'
        overlap_candidates = {"con chó", "người máy"}
        assert any(r in overlap_candidates for r in results), \
            f"Expected at least one of {overlap_candidates}, got {results}"

    def test_vietnamese_exact_length_priority(self):
        """2-word answers should prefer 2-word distractors."""
        random.seed(42)
        correct = "con người"
        pool = ["con chó", "cái bàn", "người máy thông minh", "xe"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=2)
        
        # 'con chó' and 'cái bàn' are 2 words (exact match)
        # 'người máy thông minh' is 4 words, 'xe' is 1 word
        assert len(results) == 2
        assert "người máy thông minh" not in results, \
            "4-word candidates should not be selected when 2-word options exist"

    # ------------------------------------------------------------------ #
    #  Japanese/Chinese (character-based) tests                            #
    # ------------------------------------------------------------------ #

    def test_japanese_char_overlap(self):
        """'以降' should prefer '以前' (shares '以') over '猫'."""
        random.seed(42)
        correct = "以降"
        pool = ["以前", "猫犬", "花火", "以来"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=2)
        
        assert len(results) == 2
        # '以前' and '以来' share '以' and have same char count (2)
        overlap_candidates = {"以前", "以来"}
        assert any(r in overlap_candidates for r in results), \
            f"Expected at least one of {overlap_candidates}, got {results}"

    def test_japanese_char_length_filter(self):
        """2-char answers should prefer 2-char distractors."""
        random.seed(42)
        correct = "以降"
        pool = ["以前", "花火", "人工知能", "木"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=2)
        
        assert len(results) == 2
        # '以前' and '花火' are 2 chars, '人工知能' is 4, '木' is 1
        assert "人工知能" not in results
        assert "木" not in results

    # ------------------------------------------------------------------ #
    #  Fallback tests                                                      #
    # ------------------------------------------------------------------ #

    def test_fallback_when_pool_too_small(self):
        """Should not crash when pool is smaller than requested amount."""
        results = SmartDistractorSelector.select("hello", ["world"], amount=5)
        assert len(results) == 1
        assert results[0] == "world"

    def test_empty_pool(self):
        """Should return empty list for empty pool."""
        results = SmartDistractorSelector.select("hello", [], amount=3)
        assert results == []

    def test_correct_answer_excluded_from_pool(self):
        """Correct answer should never appear in distractors."""
        correct = "apple"
        pool = ["apple", "banana", "orange", "grape"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=3)
        
        assert correct not in results
        assert len(results) == 3

    def test_no_duplicates_in_results(self):
        """Results should not contain duplicate entries."""
        correct = "con người"
        pool = ["con chó", "con chó", "cái ghế", "cái ghế", "con mèo"]
        
        results = SmartDistractorSelector.select(correct, pool, amount=3)
        
        assert len(results) == len(set(results)), \
            f"Duplicates found in results: {results}"

    # ------------------------------------------------------------------ #
    #  Random sampling test                                                #
    # ------------------------------------------------------------------ #

    def test_random_sampling_not_deterministic(self):
        """
        Multiple calls should sometimes produce different orderings
        (proving we use random.sample, not top-N).
        """
        correct = "con người"
        pool = ["con chó", "con mèo", "con gà", "con vịt", "con bò"]
        
        seen_orders = set()
        for _ in range(20):
            results = SmartDistractorSelector.select(correct, pool, amount=3)
            seen_orders.add(tuple(results))
        
        # With 5 candidates and 3 picks, we should see variety
        assert len(seen_orders) > 1, \
            "Selection appears deterministic — should use random sampling"

    # ------------------------------------------------------------------ #
    #  Integration with algorithms.py                                      #
    # ------------------------------------------------------------------ #

    def test_integration_select_choices(self):
        """Test that select_choices from algorithms.py uses the new selector."""
        from mindstack_app.modules.vocabulary.mcq.logics.algorithms import select_choices
        
        correct_item = {'text': 'con người', 'item_id': 1, 'type': 'noun'}
        distractor_pool = [
            {'text': 'con chó', 'item_id': 2, 'type': 'noun'},
            {'text': 'cái ghế', 'item_id': 3, 'type': 'noun'},
            {'text': 'người máy', 'item_id': 4, 'type': 'noun'},
            {'text': 'mèo', 'item_id': 5, 'type': 'noun'},
        ]
        
        result = select_choices(correct_item, distractor_pool, num_choices=4)
        
        assert len(result) == 4
        texts = [r['text'] for r in result]
        assert 'con người' in texts  # correct answer must be present


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])

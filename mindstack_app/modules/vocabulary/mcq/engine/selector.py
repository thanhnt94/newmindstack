"""
Smart Distractor Selector for MCQ Generation.
================================================
Implements a safe 4-step pipeline:
1. Pre-filtering (Exact Match)
2. Fallback Mechanism (Ensure quantity)
3. Trickiness Scoring (Visual/Morphological Traps)
4. Final Selection (Shuffle & Sort)

Pure logic — no Database access, no Flask.
"""

import random
import re
from typing import List, Set, Dict


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers) for MCQ.
    """

    @classmethod
    def select(
        cls,
        correct_item: Dict,
        candidate_pool: List[Dict],
        amount: int = 3,
    ) -> List[Dict]:
        """
        Main pipeline to select distractors.
        
        Args:
            correct_item: Dict containing {'front': str, 'back': str, 'text': str}
            candidate_pool: List of dicts containing {'front': str, 'back': str, 'text': str, ...}
            amount: Number of distractors needed.
        """
        if not candidate_pool or amount <= 0:
            return []

        # Step 1: Pre-filtering (Hard Filter)
        valid_candidates = cls._filter_exact_matches(correct_item, candidate_pool)

        # Step 2: Fallback Mechanism
        if len(valid_candidates) < amount:
            # If not enough candidates after strict filtering, fallback to a looser filter
            valid_candidates = [
                cand for cand in candidate_pool 
                if cand.get('text', '').strip().lower() != correct_item.get('text', '').strip().lower()
            ]

        if not valid_candidates:
            return []

        # Step 3: Trickiness Scoring
        scored_candidates = cls._score_candidates(correct_item, valid_candidates)

        # Step 4: Final Selection
        # Shuffle first to randomize ties
        random.shuffle(scored_candidates)
        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Return top N candidates
        return [cand for score, cand in scored_candidates[:amount]]

    @classmethod
    def _filter_exact_matches(cls, correct_item: Dict, pool: List[Dict]) -> List[Dict]:
        """
        Removes distractors that match correct_item exactly on front, back, or display text.
        """
        c_front = correct_item.get('front', '').strip().lower()
        c_back = correct_item.get('back', '').strip().lower()
        c_text = correct_item.get('text', '').strip().lower()
        
        valid = []
        for cand in pool:
            d_front = cand.get('front', '').strip().lower()
            d_back = cand.get('back', '').strip().lower()
            d_text = cand.get('text', '').strip().lower()
            
            # Rule: Must be different on ALL critical fields to be considered a "hard" distractor
            if d_front == c_front:
                continue
            if d_back == c_back:
                continue
            if d_text == c_text:
                continue
                
            valid.append(cand)
        return valid

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """Returns string representing composition: K (Kanji), H (Hiragana), C (Katakana)."""
        pattern = []
        for char in text:
            if '\u4e00' <= char <= '\u9faf': pattern.append('K')
            elif '\u3040' <= char <= '\u309f': pattern.append('H')
            elif '\u30a0' <= char <= '\u30ff': pattern.append('C')
        return "".join(pattern)

    @classmethod
    def _extract_kanji(cls, text: str) -> Set[str]:
        """Extracts a set of all Kanji characters from a string."""
        return {char for char in text if '\u4e00' <= char <= '\u9faf'}

    @classmethod
    def _score_candidates(cls, correct_item: Dict, candidates: List[Dict]) -> List[tuple]:
        """
        Scores candidates based on visual/morphological similarity to the correct item.
        """
        c_front = correct_item.get('front', '')
        c_kanji = cls._extract_kanji(c_front)
        c_pattern = cls._get_jp_pattern(c_front)
        c_len = len(c_front)
        
        scored = []
        for cand in candidates:
            score = 0
            d_front = cand.get('front', '')
            d_kanji = cls._extract_kanji(d_front)
            d_pattern = cls._get_jp_pattern(d_front)
            d_len = len(d_front)
            
            # 1. Shared Kanji (Very High Weight: +50)
            if c_kanji.intersection(d_kanji):
                score += 50
                
            # 2. Length Similarity (+10 for exact, +5 for close)
            len_diff = abs(c_len - d_len)
            if len_diff == 0:
                score += 10
            elif len_diff <= 2:
                score += 5
                
            # 3. Japanese Pattern Match (+20 for exact pattern)
            if d_pattern and d_pattern == c_pattern:
                score += 20
                
            scored.append((score, cand))
            
        return scored

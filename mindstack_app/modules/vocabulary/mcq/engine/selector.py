"""
Smart Distractor Selector for MCQ Generation.
================================================
Updated Logic: Morphological Priority
1. Pattern Analysis (e.g., "KK" for 招待)
2. Strict Pattern Filtering (Only pick same-pattern distractors if available)
3. Exclusion of exact matches
4. High-weight Shared Kanji Scoring

Pure logic — no Database access, no Flask.
"""

import random
import re
from typing import List, Set, Dict


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers) for MCQ.
    Focuses on morphological traps (same length, same Japanese pattern).
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
        """
        if not candidate_pool or amount <= 0:
            return []

        # Step 1: Pattern Analysis & Strict Filtering
        c_front = correct_item.get('front', '').strip()
        target_pattern = cls._get_jp_pattern(c_front)
        
        # Categorize candidates by pattern
        same_pattern_pool = []
        other_pool = []
        
        for cand in candidate_pool:
            d_front = cand.get('front', '').strip()
            # Hard Filter 1: Exact Match (already in _filter_logic but let's be safe)
            if not cls._is_not_exact_match(correct_item, cand):
                continue
                
            if cls._get_jp_pattern(d_front) == target_pattern:
                same_pattern_pool.append(cand)
            else:
                other_pool.append(cand)

        # "Ưu tiên hình thái và chỉ lấy những từ đó nếu đủ"
        if len(same_pattern_pool) >= amount:
            final_pool = same_pattern_pool
        else:
            # Fallback: Mix if same-pattern is not enough
            final_pool = same_pattern_pool + other_pool

        if not final_pool:
            return []

        # Step 2: Scoring (Emphasis on Shared Kanji within the pool)
        scored_candidates = cls._score_candidates(correct_item, final_pool)

        # Step 3: Final Selection
        random.shuffle(scored_candidates)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        return [cand for score, cand in scored_candidates[:amount]]

    @classmethod
    def _is_not_exact_match(cls, correct_item: Dict, cand: Dict) -> bool:
        """Helper for basic exclusion."""
        c_front = correct_item.get('front', '').strip().lower()
        c_back = correct_item.get('back', '').strip().lower()
        c_text = correct_item.get('text', '').strip().lower()
        
        d_front = cand.get('front', '').strip().lower()
        d_back = cand.get('back', '').strip().lower()
        d_text = cand.get('text', '').strip().lower()
        
        return not (d_front == c_front or d_back == c_back or d_text == c_text)

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """
        Returns string representing composition: K (Kanji), H (Hiragana), C (Katakana).
        Example: "招待" -> "KK", "招く" -> "KH"
        """
        pattern = []
        for char in text:
            if '\u4e00' <= char <= '\u9faf': pattern.append('K')
            elif '\u3040' <= char <= '\u309f': pattern.append('H')
            elif '\u30a0' <= char <= '\u30ff': pattern.append('C')
            else: pattern.append('O') # Other/Romaji
        return "".join(pattern)

    @classmethod
    def _extract_kanji(cls, text: str) -> Set[str]:
        """Extracts a set of all Kanji characters from a string."""
        return {char for char in text if '\u4e00' <= char <= '\u9faf'}

    @classmethod
    def _score_candidates(cls, correct_item: Dict, candidates: List[Dict]) -> List[tuple]:
        """
        Scores candidates. Within the same pattern, Shared Kanji is king.
        """
        c_front = correct_item.get('front', '')
        c_kanji = cls._extract_kanji(c_front)
        c_pattern = cls._get_jp_pattern(c_front)
        
        scored = []
        for cand in candidates:
            score = 0
            d_front = cand.get('front', '')
            d_kanji = cls._extract_kanji(d_front)
            d_pattern = cls._get_jp_pattern(d_front)
            
            # 1. Pattern Match Bonus (Already filtered but good for mixed fallback)
            if d_pattern == c_pattern:
                score += 100
            
            # 2. Shared Kanji (Massive trap: +50 per Kanji)
            shared_kanji = c_kanji.intersection(d_kanji)
            score += len(shared_kanji) * 50
            
            # 3. Length Similarity
            if len(d_front) == len(c_front):
                score += 20
                
            scored.append((score, cand))
            
        return scored

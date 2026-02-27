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

from mindstack_app.utils.content_renderer import strip_bbcode


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
        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        target_pattern = cls._get_jp_pattern(c_disp)
        
        # Categorize candidates by pattern
        same_pattern_pool = []
        other_pool = []
        
        for cand in candidate_pool:
            d_disp = strip_bbcode(cand.get('text', '')).strip()
            # Hard Filter: Exact Match
            if not cls._is_not_exact_match(correct_item, cand):
                continue
                
            if cls._get_jp_pattern(d_disp) == target_pattern:
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
        c_q_text = correct_item.get('q_text', '').strip().lower()
        
        d_front = cand.get('front', '').strip().lower()
        d_back = cand.get('back', '').strip().lower()
        d_text = cand.get('text', '').strip().lower()
        
        return not (d_front == c_front or d_back == c_back or d_text == c_text or (c_q_text and d_text == c_q_text))

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """
        Returns string representing composition: K (Kanji), H (Hiragana), C (Katakana).
        For Non-JP content (Vietnamese/English), returns word count "WX".
        Example: "招待" -> "KK", "Đồng nghiệp" -> "W2"
        """
        if not text: return ""
        
        # Check if contains ANY Japanese characters
        is_jp = any(('\u4e00' <= c <= '\u9fff') or ('\u3400' <= c <= '\u4dbf') or 
                    ('\u3040' <= c <= '\u309f') or ('\u30a0' <= c <= '\u30ff') 
                    for c in text)
        
        if is_jp:
            pattern = []
            for char in text:
                # Robust Kanji range: Common + Extension A
                if ('\u4e00' <= char <= '\u9fff') or ('\u3400' <= char <= '\u4dbf'):
                    pattern.append('K')
                elif '\u3040' <= char <= '\u309f': pattern.append('H')
                elif '\u30a0' <= char <= '\u30ff': pattern.append('C')
                else: pattern.append('O') # Other/Romaji
            return "".join(pattern)
        else:
            # Vietnamese/English: Count words
            words = [w for w in re.split(r'\s+', text.strip()) if w]
            return f"W{len(words)}"

    @classmethod
    def _extract_tokens(cls, text: str) -> Set[str]:
        """
        Extracts comparison tokens:
        - If Kanji present: returns set of Kanji.
        - Otherwise: returns set of normalized words (lowercase, stripped).
        """
        kanji = {char for char in text if ('\u4e00' <= char <= '\u9fff') or ('\u3400' <= char <= '\u4dbf')}
        if kanji:
            return kanji
        
        # Vietnamese/English/Non-Kanji: Split by whitespace and common punctuation
        words = {w.strip().lower() for w in re.split(r'[\s,.;/|]+', text) if len(w.strip()) > 1}
        return words

    @classmethod
    def _score_candidates(cls, correct_item: Dict, candidates: List[Dict]) -> List[tuple]:
        """
        Scores candidates based on pattern, shared tokens (Kanji/Words), and POS.
        """
        # Use display 'text' for pattern and tokens, as that's what the user sees
        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        c_pattern = cls._get_jp_pattern(c_disp)
        c_tokens = cls._extract_tokens(c_disp)
        c_type = correct_item.get('type', '').strip().lower()
        
        scored = []
        for cand in candidates:
            score = 0
            d_disp = strip_bbcode(cand.get('text', '')).strip()
            d_pattern = cls._get_jp_pattern(d_disp)
            d_tokens = cls._extract_tokens(d_disp)
            d_type = cand.get('type', '').strip().lower()
            
            # 1. Pattern Match Bonus (+100)
            if d_pattern == c_pattern:
                score += 100
            
            # 2. Shared Tokens (Kanji bẫy or Word bẫy: +150 per token)
            shared_tokens = c_tokens.intersection(d_tokens)
            score += len(shared_tokens) * 150
            
            # 3. Length Similarity (+20)
            if len(d_disp) == len(c_disp):
                score += 20
                
            # 4. Grammatical Type Match (+30)
            if d_type and c_type and d_type == c_type:
                score += 30
                
            scored.append((score, cand))
            
        return scored

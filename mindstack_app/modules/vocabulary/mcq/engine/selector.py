"""
Smart Distractor Selector for MCQ Generation.
================================================
Updated Logic v3: Morphological Priority + Multi-Correct-Answer Prevention

Core Rules:
1. NO duplicate display text (absolute dedup)
2. NO "multiple correct answers" — if a distractor's meaning overlaps
   significantly with the correct answer's meaning, it MUST be excluded
3. Pattern-based filtering for Japanese (Kanji/Kana structure)
4. Token-based overlap PENALTY for Vietnamese/non-JP answer text
5. Comma-separated Vietnamese terms are split into individual tokens

Pure logic — no Database access, no Flask.
"""

import random
import re
from typing import List, Set, Dict, Optional

from mindstack_app.utils.content_renderer import strip_bbcode


# Threshold: if >= this fraction of tokens overlap, treat as "same meaning"
_MEANING_OVERLAP_THRESHOLD = 0.6


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers) for MCQ.
    Focuses on morphological traps (same length, same Japanese pattern).
    Prevents answer-token leaking, duplicates, and multiple-correct-answer traps.
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

        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        c_back = strip_bbcode(correct_item.get('back', '')).strip()
        c_q_text = strip_bbcode(correct_item.get('q_text', '')).strip()
        target_pattern = cls._get_jp_pattern(c_disp)

        # Pre-compute correct answer tokens for filtering
        c_disp_tokens = cls._extract_tokens(c_disp)
        c_back_tokens = cls._extract_tokens(c_back)
        c_q_tokens = cls._extract_tokens(c_q_text) if c_q_text else set()

        # ── Step 1: Hard Filter + Dedup ──
        same_pattern_pool = []
        other_pool = []
        seen_texts: set[str] = set()
        seen_texts.add(c_disp.lower())  # exclude correct answer text itself

        for cand in candidate_pool:
            d_disp = strip_bbcode(cand.get('text', '')).strip()
            d_disp_lower = d_disp.lower()

            # ── Hard Filter 1: Exact identity checks ──
            if not cls._is_not_exact_match(correct_item, cand):
                continue

            # ── Hard Filter 2: Display text dedup (absolute) ──
            if d_disp_lower in seen_texts:
                continue

            # ── Hard Filter 3: Meaning overlap → multiple-correct-answer ──
            # If the distractor's BACK (meaning) overlaps heavily with:
            #   a) the correct answer's displayed text (answer side), OR
            #   b) the correct answer's BACK (meaning side), OR
            #   c) the question text (prevents circular matches)
            # → EXCLUDE it because the user cannot distinguish correct from wrong.
            d_back = strip_bbcode(cand.get('back', '')).strip()
            d_disp_tokens = cls._extract_tokens(d_disp)
            d_back_tokens = cls._extract_tokens(d_back)

            # Check: distractor display text vs correct answer display text
            if cls._tokens_overlap_high(d_disp_tokens, c_disp_tokens):
                continue

            # Check: distractor back vs correct answer back (same meaning)
            if c_back_tokens and d_back_tokens:
                if cls._tokens_overlap_high(d_back_tokens, c_back_tokens):
                    continue

            # Check: distractor display text vs question text (would be another correct answer)
            if c_q_tokens and cls._tokens_overlap_high(d_disp_tokens, c_q_tokens):
                continue

            # Check: distractor back vs question text
            if c_q_tokens and d_back_tokens:
                if cls._tokens_overlap_high(d_back_tokens, c_q_tokens):
                    continue

            seen_texts.add(d_disp_lower)

            if cls._get_jp_pattern(d_disp) == target_pattern:
                same_pattern_pool.append(cand)
            else:
                other_pool.append(cand)

        # ── Step 2: Pool selection ──
        if len(same_pattern_pool) >= amount:
            final_pool = same_pattern_pool
        else:
            final_pool = same_pattern_pool + other_pool

        if not final_pool:
            return []

        # ── Step 3: Scoring ──
        scored_candidates = cls._score_candidates(correct_item, final_pool)

        # ── Step 4: Final selection with uniqueness enforcement ──
        random.shuffle(scored_candidates)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        selected = []
        selected_texts: set[str] = set()
        selected_texts.add(c_disp.lower())

        for score, cand in scored_candidates:
            if len(selected) >= amount:
                break
            cand_text = strip_bbcode(cand.get('text', '')).strip().lower()
            if cand_text not in selected_texts:
                selected.append(cand)
                selected_texts.add(cand_text)

        return selected

    # ─────── Hard-Filter Helpers ───────

    @classmethod
    def _is_not_exact_match(cls, correct_item: Dict, cand: Dict) -> bool:
        """
        Returns True if the candidate is a valid distractor (not identical to correct answer).
        """
        def clean(t):
            return strip_bbcode(str(t or '')).strip().lower()

        c_front = clean(correct_item.get('front'))
        c_back = clean(correct_item.get('back'))
        c_text = clean(correct_item.get('text'))
        c_q_text = clean(correct_item.get('q_text'))

        d_front = clean(cand.get('front'))
        d_back = clean(cand.get('back'))
        d_text = clean(cand.get('text'))

        # 1. Morphological identity — any field matches exactly → reject
        if d_front and c_front and d_front == c_front: return False
        if d_back and c_back and d_back == c_back: return False
        if d_text and c_text and d_text == c_text: return False

        # 2. Semantic overlap — distractor label = question text
        if c_q_text and d_text == c_q_text: return False

        # 3. Distractor meaning matches question text
        if c_q_text and d_back and d_back == c_q_text: return False

        # 4. Distractor meaning matches correct answer label (cyclic)
        if c_text and d_back and d_back == c_text: return False

        return True

    @classmethod
    def _tokens_overlap_high(cls, tokens_a: Set[str], tokens_b: Set[str]) -> bool:
        """
        Returns True if two token sets overlap significantly (>= threshold).
        Uses the SMALLER set as the denominator to catch subset relationships.
        
        Example:
            tokens_a = {"cực", "kỳ", "kinh", "khùng"}
            tokens_b = {"cực", "kỳ"}
            overlap = 2/2 = 100% → True (b is a subset of a)
        """
        if not tokens_a or not tokens_b:
            return False

        shared = tokens_a.intersection(tokens_b)
        if not shared:
            return False

        # Use the smaller set as denominator → catches subset relationships
        smaller_size = min(len(tokens_a), len(tokens_b))
        ratio = len(shared) / smaller_size

        return ratio >= _MEANING_OVERLAP_THRESHOLD

    # ─────── Pattern / Token Helpers ───────

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """
        Returns string representing composition: K (Kanji), H (Hiragana), C (Katakana).
        For Non-JP content (Vietnamese/English), returns word count "WX".
        Example: "招待" -> "KK", "Đồng nghiệp" -> "W2"
        """
        if not text:
            return ""

        is_jp = any(
            ('\u4e00' <= c <= '\u9fff') or ('\u3400' <= c <= '\u4dbf') or
            ('\u3040' <= c <= '\u309f') or ('\u30a0' <= c <= '\u30ff')
            for c in text
        )

        if is_jp:
            pattern = []
            for char in text:
                if ('\u4e00' <= char <= '\u9fff') or ('\u3400' <= char <= '\u4dbf'):
                    pattern.append('K')
                elif '\u3040' <= char <= '\u309f':
                    pattern.append('H')
                elif '\u30a0' <= char <= '\u30ff':
                    pattern.append('C')
                else:
                    pattern.append('O')
            return "".join(pattern)
        else:
            words = [w for w in re.split(r'\s+', text.strip()) if w]
            return f"W{len(words)}"

    @classmethod
    def _extract_tokens(cls, text: str) -> Set[str]:
        """
        Extracts comparison tokens.
        - Japanese: returns set of Kanji characters.
        - Vietnamese/English: splits by whitespace, commas, semicolons, slashes
          and returns words with length > 1.
        """
        if not text:
            return set()

        kanji = {
            char for char in text
            if ('\u4e00' <= char <= '\u9fff') or ('\u3400' <= char <= '\u4dbf')
        }
        if kanji:
            return kanji

        # Vietnamese/English: split by whitespace AND punctuation
        words = {
            w.strip().lower()
            for w in re.split(r'[\s,.;:/|()]+', text)
            if len(w.strip()) > 1
        }
        return words

    # ─────── Scoring ───────

    @classmethod
    def _score_candidates(cls, correct_item: Dict, candidates: List[Dict]) -> List[tuple]:
        """
        Scores candidates. At this point all candidates have passed hard filters,
        so none should be duplicates or multiple-correct-answers.
        
        Scoring priorities:
        - Pattern match bonus (same JP structure)
        - PENALTY for shared answer-text tokens (keyword leak)
        - Bonus for question-side (front) token overlap (good trap)
        - Length similarity
        - Grammatical type match
        """
        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        c_pattern = cls._get_jp_pattern(c_disp)
        c_answer_tokens = cls._extract_tokens(c_disp)
        c_type = correct_item.get('type', '').strip().lower()

        c_front = strip_bbcode(correct_item.get('front', '')).strip()
        c_front_tokens = cls._extract_tokens(c_front)

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

            # 2. PENALTY for shared answer-tokens (-200 per token)
            shared_answer_tokens = c_answer_tokens.intersection(d_tokens)
            score -= len(shared_answer_tokens) * 200

            # 3. Bonus for shared QUESTION-SIDE tokens (+80 per token)
            d_front = strip_bbcode(cand.get('front', '')).strip()
            d_front_tokens = cls._extract_tokens(d_front)
            shared_front_tokens = c_front_tokens.intersection(d_front_tokens)
            score += len(shared_front_tokens) * 80

            # 4. Length Similarity (+20)
            if len(d_disp) == len(c_disp):
                score += 20

            # 5. Grammatical Type Match (+30)
            if d_type and c_type and d_type == c_type:
                score += 30

            scored.append((score, cand))

        return scored

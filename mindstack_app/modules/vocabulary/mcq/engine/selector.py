"""
Smart Distractor Selector for MCQ Generation.
================================================
Updated Logic v4: Language-Aware Scoring

Core Rules:
1. NO duplicate display text (absolute dedup)
2. NO "multiple correct answers" — meaning overlap exclusion
   (only for Vietnamese/non-JP back content, NOT for Japanese display text)
3. Pattern-based filtering for Japanese (Kanji/Kana structure)
4. LANGUAGE-AWARE scoring:
   - Japanese kanji overlap → BONUS (+150 per shared kanji = harder traps)
   - Vietnamese word overlap → PENALTY (-200 per shared word = prevents leaking)
5. Comma-separated Vietnamese terms are split into tokens

Pure logic — no Database access, no Flask.
"""

import random
import re
from typing import List, Set, Dict

from mindstack_app.utils.content_renderer import strip_bbcode


# Threshold: if >= this fraction of tokens overlap, treat as "same meaning"
_MEANING_OVERLAP_THRESHOLD = 0.6


def _is_japanese(text: str) -> bool:
    """Returns True if the text contains Japanese characters (Kanji/Hiragana/Katakana)."""
    return any(
        ('\u4e00' <= c <= '\u9fff') or ('\u3400' <= c <= '\u4dbf') or
        ('\u3040' <= c <= '\u309f') or ('\u30a0' <= c <= '\u30ff')
        for c in text
    )


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers) for MCQ.
    Language-aware: Japanese kanji overlap = good trap, Vietnamese word overlap = bad leak.
    """

    @classmethod
    def select(
        cls,
        correct_item: Dict,
        candidate_pool: List[Dict],
        amount: int = 3,
    ) -> List[Dict]:
        """Main pipeline to select distractors."""
        if not candidate_pool or amount <= 0:
            return []

        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        c_back = strip_bbcode(correct_item.get('back', '')).strip()
        c_q_text = strip_bbcode(correct_item.get('q_text', '')).strip()
        target_pattern = cls._get_jp_pattern(c_disp)

        # Detect language of the answer text (displayed choices)
        answer_is_jp = _is_japanese(c_disp)

        # Pre-compute tokens for meaning-overlap checks (Vietnamese/non-JP only)
        c_back_tokens = cls._extract_tokens(c_back) if not _is_japanese(c_back) else set()
        c_q_tokens = cls._extract_tokens(c_q_text) if c_q_text and not _is_japanese(c_q_text) else set()
        # For Vietnamese answer text overlap check
        c_disp_tokens_vn = cls._extract_tokens(c_disp) if not answer_is_jp else set()

        # ── Step 1: Hard Filter + Dedup ──
        same_pattern_pool = []
        other_pool = []
        seen_texts: set[str] = set()
        seen_texts.add(c_disp.lower())

        for cand in candidate_pool:
            d_disp = strip_bbcode(cand.get('text', '')).strip()
            d_disp_lower = d_disp.lower()

            # Hard Filter 1: Exact identity checks
            if not cls._is_not_exact_match(correct_item, cand):
                continue

            # Hard Filter 2: Display text dedup (absolute)
            if d_disp_lower in seen_texts:
                continue

            # Hard Filter 3: Meaning overlap → multiple-correct-answer
            # ONLY apply to Vietnamese/non-JP back content
            d_back = strip_bbcode(cand.get('back', '')).strip()

            if not _is_japanese(d_back) and c_back_tokens:
                d_back_tokens = cls._extract_tokens(d_back)
                # Distractor back vs correct answer back (same meaning)
                if cls._tokens_overlap_high(d_back_tokens, c_back_tokens):
                    continue

            # Vietnamese display text overlap check (not for Japanese display)
            if not answer_is_jp and c_disp_tokens_vn:
                d_disp_tokens = cls._extract_tokens(d_disp)
                if cls._tokens_overlap_high(d_disp_tokens, c_disp_tokens_vn):
                    continue

            # Question text overlap (distractor back/text vs question)
            if c_q_tokens:
                d_back_tokens_q = cls._extract_tokens(d_back) if not _is_japanese(d_back) else set()
                if d_back_tokens_q and cls._tokens_overlap_high(d_back_tokens_q, c_q_tokens):
                    continue
                # Distractor display vs question (only for Vietnamese display)
                if not answer_is_jp:
                    d_disp_tokens_q = cls._extract_tokens(d_disp)
                    if cls._tokens_overlap_high(d_disp_tokens_q, c_q_tokens):
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

        # ── Step 3: Language-aware scoring ──
        scored_candidates = cls._score_candidates(correct_item, final_pool, answer_is_jp)

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
        """Returns True if the candidate is NOT identical to correct answer."""
        def clean(t):
            return strip_bbcode(str(t or '')).strip().lower()

        c_front = clean(correct_item.get('front'))
        c_back = clean(correct_item.get('back'))
        c_text = clean(correct_item.get('text'))
        c_q_text = clean(correct_item.get('q_text'))

        d_front = clean(cand.get('front'))
        d_back = clean(cand.get('back'))
        d_text = clean(cand.get('text'))

        # Morphological identity
        if d_front and c_front and d_front == c_front: return False
        if d_back and c_back and d_back == c_back: return False
        if d_text and c_text and d_text == c_text: return False

        # Semantic overlap
        if c_q_text and d_text == c_q_text: return False
        if c_q_text and d_back and d_back == c_q_text: return False
        if c_text and d_back and d_back == c_text: return False

        return True

    @classmethod
    def _tokens_overlap_high(cls, tokens_a: Set[str], tokens_b: Set[str]) -> bool:
        """Returns True if two token sets overlap >= threshold (using smaller set as denominator)."""
        if not tokens_a or not tokens_b:
            return False
        shared = tokens_a.intersection(tokens_b)
        if not shared:
            return False
        smaller_size = min(len(tokens_a), len(tokens_b))
        return len(shared) / smaller_size >= _MEANING_OVERLAP_THRESHOLD

    # ─────── Pattern / Token Helpers ───────

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """Returns JP character composition pattern or word count for non-JP."""
        if not text:
            return ""
        if _is_japanese(text):
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
        - Japanese: set of Kanji characters.
        - Vietnamese/English: set of words split by whitespace/punctuation.
        """
        if not text:
            return set()
        kanji = {
            char for char in text
            if ('\u4e00' <= char <= '\u9fff') or ('\u3400' <= char <= '\u4dbf')
        }
        if kanji:
            return kanji
        words = {
            w.strip().lower()
            for w in re.split(r'[\s,.;:/|()]+', text)
            if len(w.strip()) > 1
        }
        return words

    # ─────── Language-Aware Scoring ───────

    @classmethod
    def _score_candidates(cls, correct_item: Dict, candidates: List[Dict],
                          answer_is_jp: bool) -> List[tuple]:
        """
        Scores candidates with LANGUAGE-AWARE logic:
        - Japanese answer: shared Kanji → BONUS (+150) = harder, better traps
        - Vietnamese answer: shared words → PENALTY (-200) = prevents keyword leaking
        """
        c_disp = strip_bbcode(correct_item.get('text', '')).strip()
        c_pattern = cls._get_jp_pattern(c_disp)
        c_tokens = cls._extract_tokens(c_disp)
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

            # 2. LANGUAGE-AWARE Token Scoring
            shared_tokens = c_tokens.intersection(d_tokens)
            if answer_is_jp:
                # Japanese: shared Kanji = GOOD trap → BONUS
                score += len(shared_tokens) * 150
            else:
                # Vietnamese/English: shared words = keyword leak → PENALTY
                score -= len(shared_tokens) * 200

            # 3. Bonus for shared QUESTION-SIDE (front) tokens (+80)
            d_front = strip_bbcode(cand.get('front', '')).strip()
            d_front_tokens = cls._extract_tokens(d_front)
            shared_front = c_front_tokens.intersection(d_front_tokens)
            score += len(shared_front) * 80

            # 4. Length Similarity (+20)
            if len(d_disp) == len(c_disp):
                score += 20

            # 5. Grammatical Type Match (+30)
            if d_type and c_type and d_type == c_type:
                score += 30

            scored.append((score, cand))

        return scored

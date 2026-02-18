"""
Smart Distractor Selector for MCQ Generation.
================================================
Replaces naive random distractor selection with an intelligent algorithm
that considers word/character length similarity and content overlap.

Pure logic — no Database access, no Flask.
"""

import random
from typing import List, Optional


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers) that are similar in
    shape and content to the correct answer, making MCQ questions harder
    and more educational.

    Algorithm:
        1. Length Filtering   — keep candidates with matching word/char count.
        2. Similarity Scoring — rank by overlapping words or characters.
        3. Random Sampling    — sample from the top tier to avoid repetition.
        4. Fallback           — fill remaining slots from broader pools.
    """

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def select(
        cls,
        correct_answer: str,
        candidate_pool: List[str],
        amount: int = 3,
    ) -> List[str]:
        """
        Select *amount* distractors from *candidate_pool*.

        Args:
            correct_answer: The correct answer string.
            candidate_pool: All other possible answer strings (already
                            de-duplicated of the correct answer by caller).
            amount: How many distractors to return.

        Returns:
            A list of *amount* distractor strings (or fewer if the pool
            is too small).
        """
        if not candidate_pool or amount <= 0:
            return []

        # Deduplicate pool and remove the correct answer itself
        pool = list({c for c in candidate_pool if c and c != correct_answer})

        if not pool:
            return []

        is_space_sep = cls._is_space_separated(correct_answer)

        # --- Step 1: Length Filtering ---
        exact_matches, fuzzy_matches = cls._filter_by_length(
            correct_answer, pool, is_space_sep
        )

        # --- Step 2: Similarity Scoring (on exact-length matches first) ---
        high_quality = cls._score_and_filter(
            correct_answer, exact_matches, is_space_sep
        )

        # --- Step 3 + 4: Assemble final selection with fallback ---
        selected = cls._assemble(
            high_quality, exact_matches, fuzzy_matches, pool, amount
        )

        return selected

    # ------------------------------------------------------------------ #
    #  Language Detection                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_space_separated(text: str) -> bool:
        """
        Detect whether the text uses space-separated words
        (English, Vietnamese, …) vs. character-based scripts
        (Japanese, Chinese, …).
        """
        return " " in text.strip()

    # ------------------------------------------------------------------ #
    #  Step 1 — Length Filtering                                           #
    # ------------------------------------------------------------------ #

    @classmethod
    def _filter_by_length(
        cls,
        correct: str,
        pool: List[str],
        is_space_sep: bool,
    ) -> tuple:
        """
        Split *pool* into two buckets:
        - **exact_matches**: same word/char count as *correct*.
        - **fuzzy_matches**: ±1 tolerance.

        Returns:
            (exact_matches, fuzzy_matches)   — fuzzy does NOT include exact.
        """
        target_len = cls._measure_length(correct, is_space_sep)

        exact: List[str] = []
        fuzzy: List[str] = []

        for candidate in pool:
            c_len = cls._measure_length(candidate, is_space_sep)
            diff = abs(c_len - target_len)

            if diff == 0:
                exact.append(candidate)
            elif diff == 1:
                fuzzy.append(candidate)

        return exact, fuzzy

    @staticmethod
    def _measure_length(text: str, is_space_sep: bool) -> int:
        """Word count (space-sep) or character count."""
        if is_space_sep:
            return len(text.split())
        return len(text)

    # ------------------------------------------------------------------ #
    #  Step 2 — Similarity Scoring                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def _score_and_filter(
        cls,
        correct: str,
        candidates: List[str],
        is_space_sep: bool,
    ) -> List[str]:
        """
        Compute overlap between *correct* and each candidate, return
        only those with score > 0, shuffled to avoid deterministic order.
        """
        if not candidates:
            return []

        if is_space_sep:
            correct_tokens = set(correct.lower().split())
        else:
            correct_tokens = set(correct)

        scored: List[tuple] = []  # (score, candidate)

        for cand in candidates:
            if is_space_sep:
                cand_tokens = set(cand.lower().split())
            else:
                cand_tokens = set(cand)

            overlap = len(correct_tokens & cand_tokens)

            if overlap > 0:
                scored.append((overlap, cand))

        # Shuffle within each score tier so sampling is fair
        random.shuffle(scored)
        # Stable-sort descending by score (shuffle preserves tie-breaking)
        scored.sort(key=lambda x: x[0], reverse=True)

        return [cand for _, cand in scored]

    # ------------------------------------------------------------------ #
    #  Step 3 + 4 — Assembly with Fallback                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assemble(
        high_quality: List[str],
        exact_length: List[str],
        fuzzy_length: List[str],
        full_pool: List[str],
        amount: int,
    ) -> List[str]:
        """
        Pick *amount* distractors with cascading fallback:
          1. Random sample from high-quality (overlap > 0, exact length).
          2. Fill from remaining exact-length candidates.
          3. Fill from fuzzy-length candidates.
          4. Fill from the entire pool.
        """
        selected: List[str] = []
        used: set = set()

        def _pick_from(source: List[str], n: int):
            """Sample up to *n* items from *source*, avoiding duplicates."""
            available = [s for s in source if s not in used]
            pick = random.sample(available, min(n, len(available)))
            selected.extend(pick)
            used.update(pick)

        remaining = amount

        # Tier 1: High-quality candidates (scored, same length, overlap > 0)
        _pick_from(high_quality, remaining)
        remaining = amount - len(selected)

        if remaining <= 0:
            return selected

        # Tier 2: Same-length but no overlap
        _pick_from(exact_length, remaining)
        remaining = amount - len(selected)

        if remaining <= 0:
            return selected

        # Tier 3: Fuzzy-length (±1)
        _pick_from(fuzzy_length, remaining)
        remaining = amount - len(selected)

        if remaining <= 0:
            return selected

        # Tier 4: Any remaining from the full pool
        _pick_from(full_pool, remaining)

        return selected

"""
Smart Distractor Selector for MCQ Generation.
================================================
Implements a 4-step pipeline to generate high-quality, 
tricky, but absolutely mutually-exclusive distractors.

Pure logic — no Database access, no Flask.
"""

import random
import re
from typing import List, Set


# Common English/Vietnamese stop words to ignore during overlap scoring
STOP_WORDS = {
    # Vietnamese
    "là", "sự", "cái", "con", "những", "các", "một", "những", "của", "và", 
    "có", "để", "làm", "được", "bị", "trong", "trên", "dưới", "với", "cho",
    # English
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "at", "by", "for", "with", "about", "as"
}


class SmartDistractorSelector:
    """
    Selects high-quality distractors (wrong answers).
    
    Algorithm Pipeline:
        1. Fetch (handled by caller: provide random candidate pool).
        2. Absolute Filtering (Sanitize) - strict overlap checks.
        3. Trickiness Scoring - shape and keyword intersection bonuses.
        4. Final Selection & Shuffling - output top M candidates.
    """

    @classmethod
    def select(
        cls,
        correct_answer: str,
        candidate_pool: List[str],
        amount: int = 3,
    ) -> List[str]:
        """
        Main pipeline to select distractors.
        """
        if not candidate_pool or amount <= 0:
            return []

        # Step 2: Absolute Filtering (Sanitization)
        valid_candidates = cls._filter_candidates(correct_answer, candidate_pool)

        if not valid_candidates:
            return []

        # Step 3: Trickiness Scoring
        scored_candidates = cls._score_candidates(correct_answer, valid_candidates)

        # Step 4: Final Selection & Shuffling (Handled partially by the caller merging + shuffling)
        # We just return the top N here.
        
        # Take the top `amount` needed
        top_candidates = [cand for score, cand in scored_candidates[:amount]]
        
        return top_candidates

    # ------------------------------------------------------------------ #
    #  Step 2 — Absolute Filtering (Sanitize)                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def _split_meaning(cls, text: str) -> Set[str]:
        """
        Splits a vocabulary meaning string into a normalized set of base intents.
        e.g., "Màu cam, quả cam / xe cộ" -> {"màu cam", "quả cam", "xe cộ"}
        """
        if not text:
            return set()
        
        # Split by typical dictionary delimiters
        parts = re.split(r'[;/,|]+', text)
        
        # Strip whitespace and lowercase
        clean_parts = {part.strip().lower() for part in parts if part.strip()}
        return clean_parts

    @classmethod
    def _filter_candidates(cls, correct_answer: str, pool: List[str]) -> List[str]:
        """
        Discard any candidate that shares ANY meaning intent with the target.
        Also discards identical string duplicates.
        """
        target_intents = cls._split_meaning(correct_answer)
        
        valid_pool = []
        seen_texts = set()
        
        for candidate in pool:
            # Skip physical string duplicates
            if candidate.lower().strip() in seen_texts:
                continue
                
            # Skip if candidate IS the correct answer
            if candidate == correct_answer:
                continue

            cand_intents = cls._split_meaning(candidate)
            
            # Intersection Check: Is there any overlap in their meanings?
            # E.g Target = {"to eat", "consume"}, Cand = {"to drink", "consume"} -> Overlap!
            overlap = target_intents.intersection(cand_intents)
            
            if not overlap:
                valid_pool.append(candidate)
                seen_texts.add(candidate.lower().strip())
                
        return valid_pool

    # ------------------------------------------------------------------ #
    #  Step 3 — Trickiness Scoring                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_jp_pattern(cls, text: str) -> str:
        """
        Returns a string representing the Japanese composition: 
        K (Kanji), H (Hiragana), C (Katakana)
        """
        pattern = []
        for char in text:
            # Kanji (CJK Unified Ideographs)
            if '\u4e00' <= char <= '\u9faf':
                pattern.append('K')
            # Hiragana
            elif '\u3040' <= char <= '\u309f':
                pattern.append('H')
            # Katakana
            elif '\u30a0' <= char <= '\u30ff':
                pattern.append('C')
        return "".join(pattern)

    @classmethod
    def _extract_kanji(cls, text: str) -> Set[str]:
        """Extracts a set of all Kanji characters from a string."""
        return {char for char in text if '\u4e00' <= char <= '\u9faf'}

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        """Splits into words and removes punctuation for scoring overlap."""
        # Replace non-alphanumeric with space and split
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        return set(clean_text.split())

    @classmethod
    def _score_candidates(cls, correct_answer: str, valid_candidates: List[str]) -> List[tuple]:
        """
        Scores candidates based on physical similarity to the target answer.
        Returns a sorted list of tuples: [(score, candidate), ...] (Descending)
        """
        target_len_chars = len(correct_answer)
        target_len_words = len(correct_answer.split())
        target_tokens = cls._tokenize(correct_answer)
        
        # Analyze target for Japanese characteristics
        target_jp_pattern = cls._get_jp_pattern(correct_answer)
        target_kanji_set = cls._extract_kanji(correct_answer)
        has_japanese = len(target_jp_pattern) > 0
        
        scored = []
        
        for cand in valid_candidates:
            score = 0
            cand_len_chars = len(cand)
            cand_len_words = len(cand.split())
            cand_tokens = cls._tokenize(cand)
            
            # 1. Length Similarity (Characters): Smaller difference = higher score
            char_diff = abs(target_len_chars - cand_len_chars)
            score += max(0, 10 - char_diff)  # Max 10 points
            
            # 2. Word Count Similarity: Smaller difference = higher score
            word_diff = abs(target_len_words - cand_len_words)
            score += max(0, 10 - (word_diff * 3)) # Max 10 points
            
            # 3. Keyword Overlap (The Trap): 
            # If they share non-stop-words, it looks like a tricky correct answer.
            shared_tokens = target_tokens.intersection(cand_tokens)
            meaningful_shared = shared_tokens - STOP_WORDS
            
            if meaningful_shared:
                score += len(meaningful_shared) * 30  # Massive bonus
                
            # 4. Japanese Orthography Heuristics
            if has_japanese:
                cand_jp_pattern = cls._get_jp_pattern(cand)
                cand_kanji_set = cls._extract_kanji(cand)
                
                # Rule 1: Exact Pattern Match (e.g. both are "KK" -> 2 Kanji)
                if cand_jp_pattern and cand_jp_pattern == target_jp_pattern:
                    score += 50
                    
                # Rule 2: Shared Kanji (Massive trap! Target "学校" vs Cand "学生" shares "学")
                shared_kanji = target_kanji_set.intersection(cand_kanji_set)
                if shared_kanji:
                    score += len(shared_kanji) * 100
                
            scored.append((score, cand))
            
        # Pre-shuffle so that candidates with the EXACT same score are randomly ordered
        random.shuffle(scored)
        
        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored

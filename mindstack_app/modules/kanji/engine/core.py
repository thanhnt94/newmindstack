"""
Core logic for Kanji decomposition and similarity.
Pure Python - No DB, No Flask.
"""
from typing import List, Dict, Set
from ..logics.kanji_data import get_kanji_components, get_all_supported_kanji, get_manual_similarity_groups

class KanjiEngine:
    """
    Engine for processing Kanji characters with N1+ coverage.
    """
    
from typing import List, Dict, Set
from ..logics.kanji_data import get_kanji_components, get_all_supported_kanji, get_manual_similarity_groups, get_kanji_details # Added get_kanji_details

class KanjiEngine:
    """
    Engine for processing Kanji characters with N1+ coverage.
    """
    
    @staticmethod
    def decompose(kanji: str) -> List[str]:
        """
        Decomposes a Kanji into its components using the Kradfile data.
        Returns a flat list of atomic components.
        """
        if not kanji or len(kanji) != 1:
            return []
            
        return get_kanji_components(kanji)

    @staticmethod
    def _calculate_jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        """Calculates Jaccard Index between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0.0

    @classmethod
    def _calculate_similarity_score(cls, target_kanji_details: Dict, candidate_kanji_details: Dict) -> float:
        """
        Calculates a comprehensive similarity score between two Kanji based on
        their components and decomposition levels.
        """
        score = 0.0
        
        # 1. Base components similarity (from kanji_db.json 'components')
        target_comps = set(target_kanji_details.get("components", []))
        cand_comps = set(candidate_kanji_details.get("components", []))
        score += cls._calculate_jaccard_similarity(target_comps, cand_comps) * 0.4 # Weight 40%

        # 2. Hanzipy Level 2 Radicals similarity
        target_l2 = set(target_kanji_details.get("hanzipy_level2_radicals", []))
        cand_l2 = set(candidate_kanji_details.get("hanzipy_level2_radicals", []))
        score += cls._calculate_jaccard_similarity(target_l2, cand_l2) * 0.3 # Weight 30%

        # 3. Hanzipy Level 3 Strokes similarity
        target_l3 = set(target_kanji_details.get("hanzipy_level3_strokes", []))
        cand_l3 = set(candidate_kanji_details.get("hanzipy_level3_strokes", []))
        score += cls._calculate_jaccard_similarity(target_l3, cand_l3) * 0.2 # Weight 20%
        
        # 4. Manual similarity group bonus (10% + overrides)
        manual_bonus = 0.0
        similar_groups = get_manual_similarity_groups()
        for group in similar_groups:
            if target_kanji_details['kanji'] in group and candidate_kanji_details['kanji'] in group:
                manual_bonus = 0.5 # Significant bonus for manual matches
                break
        score += manual_bonus # Manual bonus is added, not weighted in base score to allow stronger influence

        return min(1.0, score) # Cap score at 1.0


    @classmethod
    def find_similar(cls, target: str, limit: int = 5) -> List[Dict]:
        """
        Finds visually similar Kanji for a given character using the full dataset
        and various decomposition levels.
        """
        if not target or len(target) != 1:
            return []
            
        target_details = get_kanji_details(target)
        if not target_details:
            return []
        target_details['kanji'] = target # Add kanji char to details for similarity calculations

        all_kanji_chars = get_all_supported_kanji()
        results = []
        
        for cand_char in all_kanji_chars:
            if cand_char == target:
                continue
            
            candidate_details = get_kanji_details(cand_char)
            if not candidate_details:
                continue
            candidate_details['kanji'] = cand_char # Add kanji char to details

            score = cls._calculate_similarity_score(target_details, candidate_details)
            if score > 0: # Only add if there's some similarity
                results.append({
                    "kanji": cand_char,
                    "score": score
                })
                
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

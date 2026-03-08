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
    def calculate_similarity(kanji1: str, kanji2: str) -> float:
        """
        Calculates a similarity score between 0.0 and 1.0.
        Based on shared components and manual similarity groups.
        """
        if kanji1 == kanji2:
            return 1.0
            
        comp1 = set(get_kanji_components(kanji1))
        comp2 = set(get_kanji_components(kanji2))
        
        # Jaccard index for shared components
        if not comp1 or not comp2:
            shared_score = 0.0
        else:
            intersection = comp1.intersection(comp2)
            union = comp1.union(comp2)
            shared_score = len(intersection) / len(union) if union else 0.0
            
        # Manual similarity group bonus
        group_bonus = 0.0
        similar_groups = get_manual_similarity_groups()
        for group in similar_groups:
            if kanji1 in group and kanji2 in group:
                group_bonus = 0.5 
                break
                
        # Final score calculation (weighted)
        return min(1.0, shared_score + group_bonus)

    @classmethod
    def find_similar(cls, target: str, limit: int = 5) -> List[Dict]:
        """
        Finds visually similar Kanji for a given character using the full dataset.
        """
        if not target or len(target) != 1:
            return []
            
        target_comps = set(get_kanji_components(target))
        if not target_comps:
            return []

        all_kanji = get_all_supported_kanji()
        results = []
        
        for cand in all_kanji:
            if cand == target:
                continue
            
            # Optimization: Quick overlap check before full Jaccard
            cand_comps = get_kanji_components(cand)
            shared_count = 0
            for c in cand_comps:
                if c in target_comps:
                    shared_count += 1
            
            if shared_count > 0:
                score = shared_count / (len(target_comps) + len(cand_comps) - shared_count)
                
                # Manual bonus
                for group in get_manual_similarity_groups():
                    if target in group and cand in group:
                        score += 0.5
                        break
                
                results.append({
                    "kanji": cand,
                    "score": score
                })
                
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

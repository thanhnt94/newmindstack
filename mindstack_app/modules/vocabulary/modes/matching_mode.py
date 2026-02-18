"""
Matching Mode
=============
Matching practice mode using the Session Driver architecture.
Displays a board of pairs for the user to match.
"""

import random
from typing import Any, Dict, List, Optional
from .base_mode import BaseVocabMode, EvaluationResult

class MatchingMode(BaseVocabMode):
    """
    Matching Mode.
    
    - **Format**: Returns a set of pairs (Board) for matching.
    - **Interaction**: User matches all pairs on the board.
    - **Scoring**: Based on the number of mistakes made until the board is clear.
    """

    def get_mode_id(self) -> str:
        return 'matching'

    # ── format ───────────────────────────────────────────────────────

    def format_interaction(
        self,
        item: Dict[str, Any],
        all_items: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Matching Interaction (Board of Pairs).
        
        Logic:
        1. Take 'item' as anchor.
        2. Pick 3-5 other items from 'all_items' to fill the board.
        3. Shuffle pairs.
        """
        board_size = settings.get('board_size', 5) if settings else 5
        
        # Ensure we have a list of candidate distractors
        candidates = [i for i in (all_items or []) if i['item_id'] != item['item_id']]
        
        # Sample distractors
        num_distractors = min(len(candidates), board_size - 1)
        distractors = random.sample(candidates, num_distractors)
        
        # Build pairs
        pairs = []
        for i in [item] + distractors:
            pairs.append({
                'id': i['item_id'],
                'front': i.get('front') or (i.get('content') or {}).get('front', ''),
                'back': i.get('back') or (i.get('content') or {}).get('back', ''),
            })
            
        # Shuffle positions (Frontend will handle layout, but we provide randomized list)
        random.shuffle(pairs)
        
        return {
            'type': 'matching',
            'anchor_id': item['item_id'],
            'pairs': pairs,
            'meta': {
                'board_count': len(pairs)
            }
        }

    # ── evaluate ─────────────────────────────────────────────────────

    def evaluate_submission(
        self,
        item: Dict[str, Any],
        user_input: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate Matching session.
        """
        from mindstack_app.modules.scoring.interface import ScoringInterface
        
        mistakes = user_input.get('mistakes', 0)
        base_points = ScoringInterface.get_score_value('VOCAB_MATCHING_CORRECT_BONUS')
        
        # Threshold logic:
        # 0 mistakes = 4 quality (Easy) + Bonus
        # 1-2 mistakes = 3 quality (Good)
        # 3-4 mistakes = 2 quality (Hard)
        # >5 mistakes = 1 quality (Again)
        
        if mistakes == 0:
            quality = 4
            score_change = base_points * 2 # Bonus for perfect match
        elif mistakes <= 2:
            quality = 3
            score_change = base_points
        elif mistakes <= 4:
            quality = 2
            score_change = base_points // 2
        else:
            quality = 1
            score_change = 0
            
        return EvaluationResult(
            is_correct=(quality >= 2),
            quality=quality,
            score_change=score_change,
            feedback={
                'mistakes': mistakes,
                'is_perfect': (mistakes == 0)
            }
        )

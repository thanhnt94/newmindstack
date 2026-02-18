from typing import Dict, Any, Tuple
from ..services.scoring_config_service import ScoringConfigService

class ScoreCalculator:
    """
    Logic engine for calculating detailed scores with breakdowns.
    """
    
    @staticmethod
    def calculate(event_key: str, context: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate score with modifiers.
        
        Args:
            event_key: Base scoring event key (e.g. 'SCORE_FSRS_GOOD')
            context: {
                'difficulty': float (0-10),
                'streak': int,
                'duration_ms': int,
                'expected_duration_ms': int # Optional
            }
            
        Returns:
            (total_score, breakdown_dict)
        """
        base_score = ScoringConfigService.get_config(event_key)
        
        breakdown = {
            'base': base_score,
            'modifiers': {}
        }
        
        total = float(base_score)
        
        # 1. Difficulty Multiplier (e.g. difficulty 8.0 -> +20%)
        # Simple formula: 1.0 + (difficulty / 20) -> max 1.5 at diff=10
        difficulty = context.get('difficulty', 0.0)
        if difficulty > 0:
            mult = 1.0 + (difficulty / 20.0)
            breakdown['modifiers']['difficulty'] = round(mult, 2)
            total *= mult
            
        # 2. Streak Bonus (Flat bonus)
        streak = context.get('streak', 0)
        streak_bonus = 0
        if streak >= 5:
            streak_bonus = min(streak, 100) # Cap at 100
            breakdown['modifiers']['streak_bonus'] = streak_bonus
            total += streak_bonus
            
        # 3. Speed Bonus (if applicable)
        # speed_bonus = ...
        
        final_score = int(round(total))
        breakdown['total'] = final_score
        
        return final_score, breakdown

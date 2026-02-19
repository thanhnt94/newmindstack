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
        """
        base_score = ScoringConfigService.get_config(event_key)
        
        # Load multipliers from config
        diff_weight = ScoringConfigService.get_config('SCORING_DIFFICULTY_WEIGHT') or 20.0
        streak_threshold = ScoringConfigService.get_config('SCORING_STREAK_THRESHOLD') or 5
        streak_cap = ScoringConfigService.get_config('SCORING_STREAK_CAP') or 100
        
        breakdown = {
            'base': base_score,
            'modifiers': {}
        }
        
        total = float(base_score)
        
        # 1. Difficulty Multiplier (e.g. difficulty 8.0 -> +20% if weight=20.0)
        # Formula: 1.0 + (difficulty / difficulty_weight)
        difficulty = context.get('difficulty', 0.0)
        if difficulty > 0:
            mult = 1.0 + (difficulty / float(diff_weight))
            breakdown['modifiers']['difficulty'] = round(mult, 2)
            total *= mult
            
        # 2. Streak Bonus (Flat bonus)
        streak = context.get('streak', 0)
        streak_bonus = 0
        if streak >= streak_threshold:
            streak_bonus = min(streak, streak_cap)
            breakdown['modifiers']['streak_bonus'] = streak_bonus
            total += streak_bonus
            
        final_score = int(round(total))
        breakdown['total'] = final_score
        
        return final_score, breakdown

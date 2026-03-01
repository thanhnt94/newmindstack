from typing import Dict, Any, Tuple
from ..services.scoring_config_service import ScoringConfigService

class ScoreCalculator:
    """
    Logic engine for calculating detailed scores with breakdowns.
    """
    
    @staticmethod
    def calculate(event_key: str, context: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate score with modifiers and return a flat breakdown.
        """
        base_score = ScoringConfigService.get_config(event_key) or 0
        
        # Load multipliers from config
        diff_weight = ScoringConfigService.get_config('SCORING_DIFFICULTY_WEIGHT') or 20.0
        streak_threshold = ScoringConfigService.get_config('SCORING_STREAK_THRESHOLD') or 5
        streak_cap = ScoringConfigService.get_config('SCORING_STREAK_CAP') or 100
        
        # We'll build a flat breakdown for the UI "Receipt" style
        # format: { 'base': 15, 'difficulty': 2, 'streak': 5, 'total': 22 }
        breakdown = {
            'base': int(base_score)
        }
        
        current_total = float(base_score)
        
        # 1. Difficulty Bonus (calculated as points added)
        difficulty = context.get('difficulty', 0.0)
        if difficulty > 0:
            mult = 1.0 + (difficulty / float(diff_weight))
            new_total = current_total * mult
            diff_points = int(round(new_total - current_total))
            if diff_points > 0:
                breakdown['difficulty'] = diff_points
            current_total = new_total
            
        # 2. Streak Bonus (flat points)
        streak = context.get('streak', 0)
        if streak >= streak_threshold:
            streak_bonus = min(streak, streak_cap)
            breakdown['streak'] = streak_bonus
            current_total += streak_bonus
            
        final_score = int(round(current_total))
        breakdown['total'] = final_score
        
        # Compatibility keys
        breakdown['score_change'] = final_score
        breakdown['total_score'] = final_score
        
        return final_score, breakdown

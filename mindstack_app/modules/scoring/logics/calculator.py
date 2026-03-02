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
        Formula: Total = Base * (1 + DifficultyFactor + StabilityFactor) + StreakBonus
        """
        base_score_cfg = ScoringConfigService.get_config(event_key)
        base_score = int(base_score_cfg) if base_score_cfg is not None else 0
        
        # Load multipliers from config
        diff_weight_cfg = ScoringConfigService.get_config('SCORING_DIFFICULTY_WEIGHT')
        diff_weight = float(diff_weight_cfg) if diff_weight_cfg is not None else 20.0
        
        streak_threshold_cfg = ScoringConfigService.get_config('SCORING_STREAK_THRESHOLD')
        streak_threshold = int(streak_threshold_cfg) if streak_threshold_cfg is not None else 10
        
        streak_cap_cfg = ScoringConfigService.get_config('SCORING_STREAK_CAP')
        streak_cap = int(streak_cap_cfg) if streak_cap_cfg is not None else 10
        
        # We'll build a flat breakdown for the UI "Receipt" style
        breakdown = {
            'base': int(base_score)
        }
        
        is_correct = context.get('is_correct', True)
        if not is_correct:
            # Incorrect answer: no bonuses, just base (which is 0 for Again)
            breakdown['total'] = int(base_score)
            return int(base_score), breakdown

        current_total = float(base_score)
        
        # 1. Difficulty Bonus (Higher difficulty = more points)
        difficulty = context.get('difficulty', 0.0)
        if difficulty > 0 and diff_weight > 0:
            diff_factor = difficulty / diff_weight
            diff_points = int(round(base_score * diff_factor))
            if diff_points > 0:
                breakdown['difficulty'] = diff_points
                current_total += diff_points

        # 2. Challenge Bonus (Lower stability = more points, rewards active recall)
        stability = context.get('stability', 0.0)
        # StabilityFactor = 1.0 / (stability + 1.0). Max 1.0 bonus for new items.
        stab_factor = 1.0 / (stability + 1.0)
        stab_points = int(round(base_score * stab_factor))
        if stab_points > 0:
            breakdown['challenge'] = stab_points
            current_total += stab_points
            
        # 3. Streak Bonus (Very limited)
        streak = context.get('streak', 0)
        if streak >= streak_threshold:
            # Minimal bonus: 1 point for every 10 streaks, capped
            streak_bonus = min(streak // 10, streak_cap)
            if streak_bonus > 0:
                breakdown['streak'] = streak_bonus
                current_total += streak_bonus
            
        final_score = int(round(current_total))
        breakdown['total'] = final_score
        
        return final_score, breakdown

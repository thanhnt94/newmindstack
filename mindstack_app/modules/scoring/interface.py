# modules/scoring/interface.py
from .services.scoring_config_service import ScoringConfigService

class ScoringInterface:
    """
    Cổng giao tiếp duy nhất của module Scoring cho các module khác.
    """
    
    @staticmethod
    def get_score_value(key: str) -> int:
        """Lấy giá trị điểm cấu hình."""
        return ScoringConfigService.get_config(key)

    @staticmethod
    def award_points(user_id: int, activity_type: str):
        """
        Hàm Public để module khác yêu cầu cộng điểm.
        Thực tế nên dùng Signals, nhưng Interface này hữu ích cho các call trực tiếp nếu cần.
        """
        # Logic cộng điểm vào User model
        pass

# modules/scoring/interface.py
from .services.scoring_config_service import ScoringConfigService

class ScoringInterface:
    """
    Cổng giao tiếp duy nhất của module Scoring cho các module khác.
    """
    
    @staticmethod
    def calculate_breakdown(event_key: str, context: dict) -> tuple:
        """
        Calculate detailed score breakdown.
        Returns: (total_score, breakdown_dict)
        """
        from .logics.calculator import ScoreCalculator
        return ScoreCalculator.calculate(event_key, context)

    @staticmethod
    def get_score_value(key: str) -> int:
        """Lấy giá trị điểm cấu hình."""
        return ScoringConfigService.get_config(key)

    @staticmethod
    def award_points(user_id: int, activity_type: str, amount: int = None, item_id: int = None, item_type: str = None):
        """
        Hàm Public để module khác yêu cầu cộng điểm.
        Cập nhật User.total_score, tạo ScoreLog và phát tín hiệu score_awarded.
        """
        from mindstack_app.models import User, db, ScoreLog
        from .events import score_awarded
        
        # 1. Lấy giá trị điểm nếu không truyền vào trực tiếp
        if amount is None:
            amount = ScoringConfigService.get_config(activity_type)
            
        if not amount or amount <= 0:
            return False
            
        try:
            user = db.session.get(User, user_id)
            if not user:
                return False
                
            # 2. Cập nhật điểm tích lũy của User
            user.total_score = (user.total_score or 0) + amount
            db.session.add(user)
            
            # 3. Ghi log lịch sử điểm
            from mindstack_app.utils.db_session import safe_commit
            log = ScoreLog(
                user_id=user_id,
                score_change=amount,
                reason=activity_type,
                item_id=item_id,
                item_type=item_type
            )
            db.session.add(log)
            
            # 4. Phát tín hiệu cho các module khác (ví dụ: Gamification để kiểm tra Badge)
            score_awarded.send(None, 
                user_id=user_id, 
                amount=amount, 
                activity_type=activity_type,
                item_id=item_id,
                item_type=item_type
            )
            
            safe_commit(db.session)
            return True
        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f"Error awarding points to user {user_id}: {e}")
            return False

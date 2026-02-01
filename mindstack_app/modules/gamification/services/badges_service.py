"""
Badge Service
Logic kiểm tra và cấp phát huy hiệu (Achievements).
"""
from datetime import datetime
from mindstack_app.models import User
from mindstack_app.core.extensions import db
from flask import current_app
from ..models import Badge, UserBadge, ScoreLog


class BadgeService:
    """Dịch vụ quản lý logic cấp phát Huy hiệu (Achievements)."""

    @staticmethod
    def check_and_award_badges(user_id, trigger_type):
        """Kiểm tra và trao huy hiệu nếu đủ điều kiện."""
        try:
            from .scoring_service import ScoreService
            
            user = User.query.get(user_id)
            if not user: return []

            # Lấy tất cả badge đang active
            active_badges = Badge.query.filter_by(is_active=True).all()
            if not active_badges: return []

            # Lấy badge user đã có
            existing_badge_ids = {ub.badge_id for ub in UserBadge.query.filter_by(user_id=user_id).all()}

            new_badges = []
            
            # Tính toán các metric cần thiết một lần
            current_streak = 0
            if trigger_type == 'LOGIN' or trigger_type == 'SCORE':
                current_streak = ScoreService.calculate_current_streak(user_id)

            for badge in active_badges:
                if badge.badge_id in existing_badge_ids:
                    continue

                is_awarded = False
                
                # Logic điều kiện
                if badge.condition_type == Badge.TYPE_STREAK:
                    if current_streak >= badge.condition_value:
                        is_awarded = True
                
                elif badge.condition_type == Badge.TYPE_TOTAL_SCORE:
                     if (user.total_score or 0) >= badge.condition_value:
                        is_awarded = True
                
                # More conditions can be added here (e.g. FLASHCARD_COUNT)

                if is_awarded:
                    # Trao huy hiệu
                    ub = UserBadge(user_id=user_id, badge_id=badge.badge_id)
                    db.session.add(ub)
                    
                    # Cộng điểm thưởng badge (nếu có)
                    if badge.reward_points > 0:
                        reward_reason = f"Đạt huy hiệu: {badge.name}"
                        user.total_score = (user.total_score or 0) + badge.reward_points
                        log = ScoreLog(
                            user_id=user_id,
                            score_change=badge.reward_points,
                            reason=reward_reason,
                            item_type='BADGE_REWARD',
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(log)
                    
                    new_badges.append(badge)

            if new_badges:
                db.session.commit()

            return new_badges

        except Exception as e:
            current_app.logger.error(f"Error checking badges: {e}")
            return []

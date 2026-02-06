"""
Score Service
Logic quản lý điểm số và leaderboard.
"""
from datetime import datetime, timedelta, timezone
from mindstack_app.core.extensions import db
from mindstack_app.models import User
from ..models import ScoreLog
from flask import current_app
from sqlalchemy import func

from mindstack_app.core.signals import score_awarded
from ..logics.streak_logic import calculate_streak_from_dates


class ScoreService:
    """Dịch vụ quản lý điểm số và leaderboard."""

    @staticmethod
    def award_points(user_id, amount, reason, item_id=None, item_type=None, reference_id=None):
        """
        Cộng/trừ điểm cho user và ghi log.
        """
        if amount == 0:
            return {'success': True, 'new_total': None, 'leveled_up': False}

        try:
            user = User.query.get(user_id)
            if not user:
                current_app.logger.warning(f"Không tìm thấy user {user_id} để cộng điểm.")
                return {'success': False, 'message': 'User not found'}

            # Cập nhật điểm tổng
            old_score = user.total_score if user.total_score is not None else 0
            user.total_score = old_score + amount
            
            # Tạo log
            log = ScoreLog(
                user_id=user_id,
                item_id=item_id,
                score_change=amount,
                reason=reason,
                item_type=item_type,
                timestamp=datetime.now(timezone.utc)
            )
            
            db.session.add(log)
            db.session.commit()
            
            # Emit signal để các module khác xử lý (badges, achievements, etc.)
            score_awarded.send(
                None,
                user_id=user_id,
                amount=amount,
                reason=reason,
                new_total=user.total_score,
                item_type=item_type
            )
            
            return {
                'success': True, 
                'new_total': user.total_score,
                'score_change': amount,
                'leveled_up': False
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi khi cộng điểm cho user {user_id}: {e}", exc_info=True)
            return {'success': False, 'message': str(e)}

    @staticmethod
    def get_score_history(user_id, page=1, per_page=20):
        """Lấy lịch sử điểm của user có phân trang."""
        pagination = ScoreLog.query.filter_by(user_id=user_id)\
            .order_by(ScoreLog.timestamp.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
            
        return pagination.items, pagination.total

    @staticmethod
    def record_daily_login(user_id):
        """Ghi nhận đăng nhập hàng ngày (chỉ 1 lần/ngày)."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = ScoreLog.query.filter(
            ScoreLog.user_id == user_id,
            ScoreLog.item_type == 'LOGIN',
            ScoreLog.timestamp >= today_start
        ).first()
        
        if not existing:
            # Thưởng điểm cho việc đăng nhập
            from mindstack_app.services.config_service import get_runtime_config
            points = int(get_runtime_config('DAILY_LOGIN_SCORE', 10))
            return ScoreService.award_points(user_id, points, 'Đăng nhập hàng ngày', item_type='LOGIN')
        
        # Nếu đã login rồi thì vẫn emit signal để check badge
        score_awarded.send(
            None,
            user_id=user_id,
            amount=0,
            reason='Daily login check',
            new_total=None,
            item_type='LOGIN'
        )
        return None

    @staticmethod
    def get_leaderboard(timeframe='all_time', limit=10):
        """
        Lấy bảng xếp hạng top users.
        timeframe: 'day', 'week', 'month', 'all_time'
        """
        if timeframe == 'all_time':
            users = User.query.order_by(User.total_score.desc()).limit(limit).all()
            return [
                {
                    'username': u.username,
                    'is_current': False,
                    'score': u.total_score or 0
                } for u in users
            ]
        
        query = db.session.query(
            User.username,
            User.user_id,
            func.sum(ScoreLog.score_change).label('period_score')
        ).join(ScoreLog, User.user_id == ScoreLog.user_id)

        now = datetime.now(timezone.utc)
        if timeframe == 'day':
            start_date = now - timedelta(days=1)
            query = query.filter(ScoreLog.timestamp >= start_date)
        elif timeframe == 'week':
            start_date = now - timedelta(weeks=1)
            query = query.filter(ScoreLog.timestamp >= start_date)
        elif timeframe == 'month':
            start_date = now - timedelta(days=30)
            query = query.filter(ScoreLog.timestamp >= start_date)
        
        results = query.group_by(User.user_id, User.username)\
            .order_by(func.sum(ScoreLog.score_change).desc())\
            .limit(limit).all()
            
        return [
            {
                'username': r.username,
                'user_id': r.user_id,
                'score': int(r.period_score or 0)
            } for r in results
        ]

    @staticmethod
    def calculate_current_streak(user_id):
        """Tính chuỗi ngày hoạt động liên tục (learning streak)."""
        rows = (
            db.session.query(func.date(ScoreLog.timestamp).label('activity_date'))
            .filter(ScoreLog.user_id == user_id)
            .group_by(func.date(ScoreLog.timestamp))
            .order_by(func.date(ScoreLog.timestamp).desc())
            .all()
        )

        if not rows:
            return 0

        # Extract dates from query results and delegate to pure logic
        activity_dates = [row.activity_date for row in rows]
        return calculate_streak_from_dates(activity_dates, datetime.now(timezone.utc).date())

    @staticmethod
    def sync_user_score(user_id: int) -> int:
        """
        Đồng bộ điểm số của một user dựa trên ScoreLog.
        Cập nhật lại User.total_score.
        """
        user = User.query.get(user_id)
        if not user:
            return 0
        
        # Tính tổng điểm từ log
        total_from_log = db.session.query(func.sum(ScoreLog.score_change))\
            .filter(ScoreLog.user_id == user_id).scalar() or 0
        
        user.total_score = int(total_from_log)
        db.session.commit()
        return user.total_score

    @staticmethod
    def sync_all_users_scores() -> dict:
        """
        Đồng bộ điểm số cho tất cả người dùng từ ScoreLog.
        """
        users = User.query.all()
        synced_count = 0
        for user in users:
            # Inline summing for efficiency in loops, though scalar() is fine here
            total = db.session.query(func.sum(ScoreLog.score_change))\
                .filter(ScoreLog.user_id == user.user_id).scalar() or 0
            user.total_score = int(total)
            synced_count += 1
            
        db.session.commit()
        return {'success': True, 'synced_count': synced_count}
        return {'success': True, 'synced_count': synced_count}

    @staticmethod
    def delete_user_data(user_id: int) -> bool:
        """Delete all score logs for user (Reset Data)."""
        try:
            ScoreLog.query.filter_by(user_id=user_id).delete()
            # Note: Badges and Streaks might need resetting too if they are stored in separate tables linked to user.
            # Assuming ScoreLog is the main transactional data. 
            # Streaks are calculated from logs, so deleting logs breaks streaks implicitly (or check StreakService).
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user gamification data: {e}")
            return False

    @staticmethod
    def delete_items_data(user_id: int, item_ids: list[int]) -> bool:
        """Delete score logs for specific items."""
        try:
            if not item_ids:
                return True
            ScoreLog.query.filter(
                ScoreLog.user_id == user_id, 
                ScoreLog.item_id.in_(item_ids)
            ).delete(synchronize_session=False)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting item gamification data: {e}")
            return False

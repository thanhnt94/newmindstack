"""
Score Service
Logic quản lý điểm số và leaderboard.
"""
from datetime import datetime, timedelta
from mindstack_app.models import db, User, ScoreLog
from flask import current_app
from sqlalchemy import func


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
                timestamp=datetime.utcnow()
            )
            
            db.session.add(log)
            db.session.commit()
            
            # Kiểm tra Badges sau khi cộng điểm
            from .badges_service import BadgeService
            BadgeService.check_and_award_badges(user_id, 'SCORE')
            BadgeService.check_and_award_badges(user_id, 'LOGIN')
            
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
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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
        
        # Nếu đã login rồi thì vẫn check badge
        from .badges_service import BadgeService
        BadgeService.check_and_award_badges(user_id, 'LOGIN')
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

        now = datetime.utcnow()
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

        if not rows: return 0

        learned_dates = set()
        for row in rows:
            val = row.activity_date
            if isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val).date()
                except ValueError:
                    continue
            elif isinstance(val, datetime):
                val = val.date()
            if val: learned_dates.add(val)

        if not learned_dates: return 0

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        streak = 0
        current_check = today
        
        if today not in learned_dates:
            if yesterday in learned_dates:
                current_check = yesterday
            else:
                return 0
        
        while current_check in learned_dates:
            streak += 1
            current_check -= timedelta(days=1)
            
        return streak

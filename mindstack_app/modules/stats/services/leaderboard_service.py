from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc

from mindstack_app.models import db, User, ScoreLog
from ..logics.time_logic import TimeLogic
from ..config import StatsConfig

class LeaderboardService:
    @classmethod
    def get_leaderboard(cls, timeframe: str = None, limit: int = None, viewer_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """
        Orchestrator: Điều phối việc lấy dữ liệu bảng xếp hạng.
        """
        timeframe = timeframe or StatsConfig.DEFAULT_TIMEFRAME
        limit = limit or StatsConfig.LEADERBOARD_LIMIT
        
        # Gọi tầng Logic để tính toán mốc thời gian
        start_date = TimeLogic.get_timeframe_start(timeframe)

        query = db.session.query(
            User.user_id,
            User.username,
            User.user_role,
            User.avatar_url,
            func.sum(ScoreLog.score_change).label('score_val')
        ).join(ScoreLog, User.user_id == ScoreLog.user_id)

        if start_date:
            # SQLite comparison: Convert to naive UTC
            db_start_date = start_date.replace(tzinfo=None)
            query = query.filter(ScoreLog.timestamp >= db_start_date)

        results = (
            query
            .group_by(User.user_id, User.username, User.user_role, User.avatar_url)
            .order_by(desc('score_val'))
            .limit(limit)
            .all()
        )

        leaderboard = []
        viewer_id = viewer_user.user_id if viewer_user else None
        
        for idx, row in enumerate(results, start=1):
            # Logic xử lý Avatar
            avatar_url = None
            if row.avatar_url:
                if row.avatar_url.startswith(('http://', 'https://')):
                    avatar_url = row.avatar_url
                else:
                    from flask import url_for
                    try:
                        avatar_url = url_for('media_uploads', filename=row.avatar_url)
                    except: pass
            
            leaderboard.append({
                'rank': idx,
                'user_id': row.user_id,
                'username': row.username,
                'avatar_url': avatar_url,
                'score': int(row.score_val or 0),
                'is_current_user': (row.user_id == viewer_id)
            })
            
        return leaderboard

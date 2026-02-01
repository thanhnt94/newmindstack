from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc

from mindstack_app.models import db, User, ScoreLog

class LeaderboardService:
    @classmethod
    def get_leaderboard(cls, timeframe: str = 'all_time', limit: int = 10, viewer_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu bảng xếp hạng dựa trên mốc thời gian.
        timeframe: 'day', 'week', 'month', '30d', 'all_time'
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        start_date = None
        if timeframe == 'day':
            start_date = today_start
        elif timeframe == 'week':
            # Rolling 7 days instead of calendar week to avoid empty stats at week start
            start_date = today_start - timedelta(days=6)
        elif timeframe == 'month':
            # Rolling 30 days instead of calendar month
            start_date = today_start - timedelta(days=29)
        elif timeframe == '30d':
            start_date = today_start - timedelta(days=29)

        query = db.session.query(
            User.user_id,
            User.username,
            User.user_role,
            User.avatar_url,
            func.sum(ScoreLog.score_change).label('score_val')
        ).join(ScoreLog, User.user_id == ScoreLog.user_id)

        if start_date:
            # SQLite comparison fix: Use naive UTC to match stored format
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
            # Optimizing: Get avatar URL logic
            display_name = row.username
            is_viewer = (row.user_id == viewer_id)
            
            # Use cached url or fallback
            avatar_url = None
            if row.avatar_url:
                if row.avatar_url.startswith(('http://', 'https://')):
                    avatar_url = row.avatar_url
                else:
                    # Avoid many individual User.query.get if possible, 
                    # but for now we keep it simple or use a helper
                    from flask import url_for
                    try:
                        avatar_url = url_for('media_uploads', filename=row.avatar_url)
                    except:
                        pass
            
            leaderboard.append({
                'rank': idx,
                'user_id': row.user_id,
                'username': display_name,
                'avatar_url': avatar_url,
                'score': int(row.score_val or 0),
                'is_current_user': is_viewer
            })
            
        return leaderboard

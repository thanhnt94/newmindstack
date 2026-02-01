from datetime import datetime, timedelta, timezone

class TimeLogic:
    @staticmethod
    def get_timeframe_start(timeframe: str) -> datetime:
        """
        Logic thuần túy tính toán mốc thời gian bắt đầu.
        Không dính tới DB hay Flask context.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if timeframe == 'day':
            return today_start
        elif timeframe == 'week':
            return today_start - timedelta(days=6)
        elif timeframe == 'month':
            return today_start - timedelta(days=29)
        elif timeframe == '30d':
            return today_start - timedelta(days=29)
        
        return None # All time

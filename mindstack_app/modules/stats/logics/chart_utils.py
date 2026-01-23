"""
Chart Utilities - Pure functions for date/time handling and chart data processing.

This module contains ONLY pure Python logic.
NO database, NO Flask dependencies allowed.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Tuple, Optional, Generator, Any


# Timeframe mapping (string to days)
TIMEFRAME_DAYS = {
    '7d': 7,
    '14d': 14,
    '30d': 30,
    '90d': 90,
    '180d': 180,
    '365d': 365,
}


def resolve_timeframe_dates(timeframe: str) -> Tuple[Optional[date], date]:
    """
    Return (start_date, end_date) for the requested timeframe.
    
    Args:
        timeframe: String like '7d', '30d', '90d', '365d', or 'all'.
        
    Returns:
        Tuple of (start_date, end_date). start_date is None if timeframe='all'.
        
    Examples:
        >>> resolve_timeframe_dates('7d')
        (date(2024, 1, 17), date(2024, 1, 23))  # 7 days ago to today
        
        >>> resolve_timeframe_dates('all')
        (None, date(2024, 1, 23))
    """
    end_date = date.today()
    timeframe = (timeframe or '').lower()
    
    if timeframe == 'all':
        return None, end_date
    
    days = TIMEFRAME_DAYS.get(timeframe, 30)  # Default to 30 days
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def normalize_datetime_range(
    start_date: Optional[date], 
    end_date: Optional[date]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Return aware datetime boundaries for filtering timestamps.
    
    Converts date objects to UTC-aware datetime at start/end of day.
    
    Args:
        start_date: Start date (inclusive).
        end_date: End date (inclusive, converted to next day 00:00 for < comparison).
        
    Returns:
        Tuple of (start_dt, end_dt) as timezone-aware datetimes.
    """
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    else:
        start_dt = None

    if end_date:
        # End of day = start of next day for exclusive comparison
        end_dt = (
            datetime.combine(end_date + timedelta(days=1), datetime.min.time())
            .replace(tzinfo=timezone.utc)
        )
    else:
        end_dt = None

    return start_dt, end_dt


def date_range(start_date: date, end_date: date) -> Generator[date, None, None]:
    """
    Generate a sequence of dates from start to end (inclusive).
    
    Args:
        start_date: First date in sequence.
        end_date: Last date in sequence (inclusive).
        
    Yields:
        Each date in the range.
        
    Examples:
        >>> list(date_range(date(2024, 1, 1), date(2024, 1, 3)))
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    """
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def parse_history_datetime(raw_value: Any) -> Optional[datetime]:
    """
    Safely parse ISO formatted timestamps stored in JSON histories.
    
    Handles various input types:
    - datetime objects (returned as-is with UTC)
    - ISO format strings (with or without timezone)
    - None or invalid values (returns None)
    
    Args:
        raw_value: Value to parse (str, datetime, or None).
        
    Returns:
        UTC-aware datetime, or None if parsing fails.
    """
    if not raw_value:
        return None

    if isinstance(raw_value, datetime):
        dt_value = raw_value
    elif isinstance(raw_value, str):
        try:
            # Handle 'Z' suffix for UTC
            normalized = raw_value.replace('Z', '+00:00')
            dt_value = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    # Ensure timezone-aware
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    else:
        dt_value = dt_value.astimezone(timezone.utc)
    
    return dt_value


def sanitize_pagination(
    page: Any, 
    per_page: Any, 
    default_per_page: int = 10, 
    max_per_page: int = 50
) -> Tuple[int, int]:
    """
    Normalize pagination parameters from query strings.
    
    Args:
        page: Page number (may be string, int, or None).
        per_page: Items per page (may be string, int, or None).
        default_per_page: Default value for per_page.
        max_per_page: Maximum allowed per_page value.
        
    Returns:
        Tuple of (page, per_page) as validated integers.
        
    Examples:
        >>> sanitize_pagination('2', '25')
        (2, 25)
        
        >>> sanitize_pagination(None, '100', max_per_page=50)
        (1, 50)
    """
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    if page < 1:
        page = 1

    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = default_per_page

    if per_page < 1:
        per_page = default_per_page

    per_page = min(per_page, max_per_page)
    return page, per_page


def fill_series_gaps(
    data_map: dict,
    start_date: date,
    end_date: date,
    default_value: Any = 0
) -> list:
    """
    Fill gaps in a date series with default values.
    
    Useful for creating continuous chart data where some dates have no records.
    
    Args:
        data_map: Dict mapping dates to values.
        start_date: Start of date range.
        end_date: End of date range.
        default_value: Value to use for missing dates.
        
    Returns:
        List of dicts with 'date' and 'value' keys for each day.
    """
    series = []
    for current_date in date_range(start_date, end_date):
        value = data_map.get(current_date, default_value)
        series.append({
            'date': current_date.isoformat(),
            'value': value
        })
    return series

"""
Chart Utilities - Pure functions for date/time handling and chart data processing.

This module contains ONLY pure Python logic.
NO database, NO Flask dependencies allowed.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Tuple, Optional, Generator, Any, List, Dict


# Timeframe mapping (string to days)
TIMEFRAME_DAYS = {
    '7d': 7,
    '14d': 14,
    '30d': 30,
    '90d': 90,
    '180d': 180,
    '365d': 365,
}

# Chart Color Palette (Standardized)
CHART_COLORS = {
    'primary': 'rgba(79, 70, 229, 1)',   # Indigo 600
    'primary_bg': 'rgba(79, 70, 229, 0.1)',
    'success': 'rgba(16, 185, 129, 1)',   # Emerald 500
    'success_bg': 'rgba(16, 185, 129, 0.1)',
    'warning': 'rgba(245, 158, 11, 1)',   # Amber 500
    'warning_bg': 'rgba(245, 158, 11, 0.1)',
    'danger': 'rgba(239, 68, 68, 1)',     # Red 500
    'danger_bg': 'rgba(239, 68, 68, 0.1)',
    'info': 'rgba(59, 130, 246, 1)',      # Blue 500
    'info_bg': 'rgba(59, 130, 246, 0.1)',
    'neutral': 'rgba(107, 114, 128, 1)',  # Gray 500
}

def resolve_timeframe_dates(timeframe: str) -> Tuple[Optional[date], date]:
    """
    Return (start_date, end_date) for the requested timeframe.
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
    """
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def parse_history_datetime(raw_value: Any) -> Optional[datetime]:
    """
    Safely parse ISO formatted timestamps stored in JSON histories.
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
    Returns list of dicts with 'date' and 'value' keys.
    """
    series = []
    for current_date in date_range(start_date, end_date):
        value = data_map.get(current_date, default_value)
        series.append({
            'date': current_date.isoformat(),
            'value': value,
            'label': current_date.strftime('%d/%m')
        })
    return series

def prepare_chartjs_config(
        labels: List[str], 
        datasets: List[Dict[str, Any]], 
        chart_type: str = 'line',
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
    """
    Generate a ready-to-use Chart.js configuration dictionary.
    """
    base_config = {
        'type': chart_type,
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'position': 'bottom'
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': True
                }
            }
        }
    }
    
    if options:
        base_config['options'].update(options)
        
    return base_config

def get_color_for_dataset(index: int, alpha: float = 1.0) -> str:
    """Get a color from the predefined palette based on index."""
    colors = [
        CHART_COLORS['primary'],
        CHART_COLORS['success'],
        CHART_COLORS['warning'],
        CHART_COLORS['danger'],
        CHART_COLORS['info'],
        CHART_COLORS['neutral']
    ]
    base = colors[index % len(colors)]
    if alpha < 1.0:
        return base.replace('1)', f'{alpha})')
    return base

"""
Stateless calculation logic for Goal Progress.
Pure functions, no database dependencies.
"""

from datetime import datetime, date

def calculate_percentage(current_value: int, target_value: int) -> int:
    """Calculate integer percentage limited to 100."""
    if target_value <= 0:
        return 100 if current_value > 0 else 0
    
    percent = (current_value / target_value) * 100
    return min(100, int(percent))

def get_progress_color_class(percent: int) -> str:
    """Return CSS class suffix for progress bars."""
    if percent >= 100:
        return 'success' # Green/Complete
    if percent >= 75:
        return 'info'    # Blueish
    if percent >= 40:
        return 'primary' # Main color
    if percent > 0:
        return 'warning' # Yellow/Orange
    return 'secondary'   # Grey

def get_remaining_value(current: int, target: int) -> int:
    return max(0, target - current)

def is_goal_met(current: int, target: int) -> bool:
    return current >= target

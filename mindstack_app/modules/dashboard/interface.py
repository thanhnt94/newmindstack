from .services.dashboard_service import DashboardService

def get_dashboard_data(user_id: int):
    """Public API to get dashboard data."""
    return DashboardService.get_dashboard_data(user_id)

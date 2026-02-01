# modules/maintenance/middleware.py
from flask import request, render_template, abort, current_app, url_for, redirect
from flask_login import current_user
from mindstack_app.models import AppSettings
from .config import MaintenanceDefaultConfig

def register_maintenance_middleware(app):
    @app.before_request
    def check_maintenance_mode():
        # 1. Bypass check if in maintenance admin page itself to avoid loops
        if request.endpoint and request.endpoint.startswith('maintenance.'):
            return

        # 2. Check if Maintenance Mode is enabled in AppSettings
        is_enabled = AppSettings.get('MAINTENANCE_MODE', MaintenanceDefaultConfig.MAINTENANCE_MODE)
        
        if is_enabled:
            # Bypass for Admin Users
            if current_user.is_authenticated and current_user.user_role == 'admin':
                return
            
            # Bypass for Admin URLs, Auth URLs, and Static files
            bypass_prefixes = ['/admin', '/auth', '/static', '/api/auth']
            if any(request.path.startswith(prefix) for prefix in bypass_prefixes):
                return
            
            # Show maintenance page
            return render_template('maintenance/maintenance.html', 
                                   message=AppSettings.get('MAINTENANCE_MESSAGE', MaintenanceDefaultConfig.MAINTENANCE_MESSAGE),
                                   end_time=AppSettings.get('MAINTENANCE_END_TIME', MaintenanceDefaultConfig.MAINTENANCE_END_TIME))

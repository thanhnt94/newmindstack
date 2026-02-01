from flask import render_template, request, current_app
from flask_login import current_user

def init_maintenance_mode(app):
    """Register maintenance mode check before each request."""

    @app.before_request
    def check_maintenance_mode():
        # 1. Skip check if maintenance mode is not active
        if not current_app.config.get('MAINTENANCE_MODE'):
            return

        # 2. Skip check for static files and uploads
        if request.path.startswith('/static/') or request.path.startswith('/uploads/') or request.path == '/favicon.ico':
            return

        # 3. Allow admins to bypass maintenance
        if current_user.is_authenticated and current_user.user_role == 'admin':
            return

        # 4. Allow access to login/logout so admins can authenticate
        # Adjust these blueprint names/paths based on your app's actual auth setup
        if request.blueprint == 'auth' or request.path.startswith('/auth/'):
            return

        # 5. Allow access to admin dashboard (and login) so they can turn off maintenance
        if request.path.startswith('/admin') or request.endpoint == 'admin.login':
            return

        # 6. Prevent recursion: don't check if we are already on the maintenance-related paths if any
        # (Though we are rendering directly, so recursion isn't a typical redirect loop issue here)

        # 7. Render maintenance page
        from mindstack_app.services.template_service import TemplateService
        _v = TemplateService.get_active_version()
        
        maintenance_end_time = current_app.config.get('MAINTENANCE_END_TIME')
        
        # We use a 503 Service Unavailable status code
        return render_template(f"{_v}/pages/system/maintenance.html", 
                               maintenance_end_time=maintenance_end_time), 503

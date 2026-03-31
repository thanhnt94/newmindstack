from flask import redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import current_user
from .. import blueprint

@blueprint.route('/')
def index():
    """
    Trang chủ của ứng dụng.
    Nếu người dùng đã đăng nhập, chuyển hướng đến dashboard.
    Nếu chưa đăng nhập và dùng SSO, tự động chuyển hướng đến SSO login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    # NEW: Tự động đăng nhập nếu dùng SSO (Silent Login)
    from mindstack_app.modules.auth.services.auth_service import AuthService
    if AuthService.get_config('AUTH_PROVIDER', 'local') == 'central':
        return redirect(url_for('auth.login'))
        
    return render_dynamic_template('modules/landing/index.html')

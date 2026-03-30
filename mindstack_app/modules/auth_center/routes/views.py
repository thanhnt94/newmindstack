from flask import redirect, url_for, request, flash, current_app
from flask_login import login_user, current_user
from .. import blueprint
from ..services.sso_service import SSOService

@blueprint.route('/login')
def login():
    """Initiates the SSO Login Flow."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
        
    client = SSOService.get_client()
    if client.check_health():
        callback_url = url_for('auth_center.callback', _external=True)
        return redirect(client.get_login_url(callback_url))
    else:
        flash('Central Auth server is unreachable. Please login locally.', 'warning')
        return redirect(url_for('auth.login'))

@blueprint.route('/callback')
def callback():
    """
    V2 Callback: Receives an authorization code and performs 
    server-side token exchange.
    """
    code = request.args.get('code')
    if not code:
        flash('Xác thực SSO thất bại: Không tìm thấy mã xác thực (code).', 'danger')
        return redirect(url_for('auth.login'))
        
    user = SSOService.handle_callback(code)
    if user:
        login_user(user)
        
        try:
            from mindstack_app.core.signals import user_logged_in
            user_logged_in.send(current_app._get_current_object(), user=current_user)
        except Exception:
            pass
            
        flash('Đăng nhập qua SSO thành công!', 'success')
        return redirect(url_for('dashboard.dashboard'))
    else:
        flash('Xác thực token SSO thất bại hoặc không thể đồng bộ tài khoản.', 'danger')
        return redirect(url_for('auth.login'))

@blueprint.route('/logout')
def logout():
    """Handles Global Logout from the ecosystem."""
    from flask_login import logout_user
    from flask import session
    
    # 1. Clear local session
    logout_user()
    session.clear()
    
    # 2. Redirect to CentralAuth Logout (Global Logout)
    client = SSOService.get_client()
    # Now client.web_url is a clean base URL
    return redirect(f"{client.web_url}/api/auth/logout")

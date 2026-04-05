from flask import redirect, url_for, request, flash, current_app, session, jsonify
from flask_login import login_user, current_user
from .. import blueprint
from ..services.sso_service import SSOService
from mindstack_app.modules.auth.models import UserSSOSession
from mindstack_app.core.extensions import db
import jwt
import time

@blueprint.route('/login')
def login():
    """Initiates the SSO Login Flow. Always re-authenticates to support user switching."""
    # Removed early redirect to allow CentralAuth to dictate the active user
        
    client = SSOService.get_client()
    if client.check_health():
        callback_url = url_for('auth_center.callback', _external=True)
        return redirect(client.get_login_url(callback_url))
    else:
        flash('Central Auth server is unreachable. Please login locally.', 'warning')
        return redirect(url_for('auth.login', sso_failed=1))

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
        
        # Store Session ID for Back-channel logout tracking (Skip if already exists)
        if hasattr(session, 'sid'):
            existing_sess = UserSSOSession.query.filter_by(session_id=session.sid).first()
            if not existing_sess:
                new_sess = UserSSOSession(user_id=user.user_id, session_id=session.sid)
                db.session.add(new_sess)
                db.session.commit()
        
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
    
    # 1. Clear local session
    logout_user()
    session.clear()
    
    # 2. Redirect to CentralAuth Logout (to trigger global SLO)
    client = SSOService.get_client()
    return redirect(f"{client.web_url}/api/auth/logout")

@blueprint.route('/backchannel-logout', methods=['POST'])
def backchannel_logout():
    """
    Handle remote logout requests from CentralAuth.
    Verifies the JWT 'logout_token' and clears indexed server-side sessions.
    """
    data = request.get_json()
    logout_token = data.get('logout_token')
    
    if not logout_token:
        return jsonify({"error": "Missing logout_token"}), 400
        
    try:
        # Get the Client Secret
        # In MindStack, it's in config
        secret = current_app.config.get('CENTRAL_AUTH_CLIENT_SECRET') or current_app.config['SECRET_KEY']
        
        # Verify and decode
        payload = jwt.decode(logout_token, secret, algorithms=['HS256'])
        user_id = payload.get('sub') # CentralAuth User ID
        
        if not user_id:
            return jsonify({"error": "Invalid token"}), 400

        # Find and invalidate sessions
        user_sessions = UserSSOSession.query.filter_by(user_id=user_id).all()
        session_ids = [s.session_id for s in user_sessions]
        
        if session_ids:
            # Delete from flask-session table ('sessions')
            db.session.execute(db.text("DELETE FROM sessions WHERE session_id IN :ids"), {"ids": tuple(session_ids)})
            # Clear our tracking
            UserSSOSession.query.filter(UserSSOSession.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            current_app.logger.info(f"MindStack SLO: Invalidated {len(session_ids)} sessions for user {user_id}")
        
        return jsonify({"status": "success", "invalidated": len(session_ids)}), 200
        
    except Exception as e:
        current_app.logger.error(f"MindStack SLO Error: {e}")
        return jsonify({"error": str(e)}), 500


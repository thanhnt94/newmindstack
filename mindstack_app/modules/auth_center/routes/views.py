from flask import redirect, url_for, request, flash, current_app, session, jsonify
from flask_login import login_user, current_user
from mindstack_app.core.extensions import db, csrf_protect
from .. import blueprint
from ..services.sso_service import SSOService
from mindstack_app.modules.auth.models import User, UserSSOSession
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
        # Redirect silently to login if accessed directly without a code
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


# --- INTERNAL SSO SYNC API ---

@blueprint.route('/api/sso-internal/user-list', methods=['POST'])
@csrf_protect.exempt
def internal_user_list():
    """Returns a list of all local users for CentralAuth synchronization auditing."""
    secret = request.headers.get('X-Client-Secret')
    if secret != current_app.config.get('CENTRAL_AUTH_CLIENT_SECRET'):
        return jsonify({"error": "Unauthorized"}), 401
        
    users = User.query.all()
    user_data = []
    for u in users:
        user_data.append({
            "id": u.user_id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "central_auth_id": u.central_auth_id
        })
    return jsonify({"users": user_data}), 200

@blueprint.route('/api/sso-internal/link-user', methods=['POST'])
@csrf_protect.exempt
def internal_link_user():
    """Links a local user to a CentralAuth UUID. Supports Admin Push-Back."""
    secret = request.headers.get('X-Client-Secret')
    if secret != current_app.config.get('CENTRAL_AUTH_CLIENT_SECRET'):
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    email = data.get('email')
    ca_id = data.get('central_auth_id')
    username = data.get('username')
    full_name = data.get('full_name')
    is_admin_sync = data.get('is_admin_sync', False)
    
    if not ca_id:
        return jsonify({"error": "Missing central_auth_id"}), 400

    target_user = None

    # 1. Admin Push-back logic
    if is_admin_sync:
        # Target local ID 1
        target_user = User.query.get(1)
        if target_user:
            # Check if already linked to someone else
            if target_user.central_auth_id and target_user.central_auth_id != ca_id:
                return jsonify({"error": "Local ID 1 is already linked to a different CentralAuth account"}), 409
            
            # Perform Push-back (Overwrite local admin identity)
            target_user.username = username or target_user.username
            target_user.email = email or target_user.email
            target_user.full_name = full_name or target_user.full_name
            target_user.central_auth_id = ca_id
            db.session.commit()
            return jsonify({"status": "success", "message": f"Admin identity pushed back to local ID 1 ({target_user.username})"}), 200

    # 2. Standard linking logic
    if not target_user:
        target_user = User.query.filter_by(email=email).first()
    
    if not target_user and not is_admin_sync:
        # Try finding by username as fallback
        target_user = User.query.filter_by(username=username).first()

    if target_user:
        target_user.central_auth_id = ca_id
        if full_name: target_user.full_name = full_name
        db.session.commit()
        return jsonify({"status": "success", "message": f"User {target_user.username} linked to CentralAuth ID {ca_id}"}), 200
    
    return jsonify({"error": "User not found for linking"}), 404

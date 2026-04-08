from flask import redirect, url_for, request, flash, current_app, session, jsonify
from flask_login import login_user, current_user
from mindstack_app.core.extensions import db, csrf_protect
from .. import blueprint, internal_sync_bp
from ..services.sso_service import SSOService
from mindstack_app.modules.auth.models import User, UserSSOSession
import jwt
import time

@blueprint.route('/login')
def login():
    """Initiates the SSO Login Flow. Always re-authenticates to support user switching."""
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
        return redirect(url_for('auth.login'))
        
    user = SSOService.handle_callback(code)
    if user:
        login_user(user)
        
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
    logout_user()
    session.clear()
    client = SSOService.get_client()
    return redirect(f"{client.web_url}/api/auth/logout")

@blueprint.route('/backchannel-logout', methods=['POST'])
def backchannel_logout():
    """Handle remote logout requests from CentralAuth."""
    data = request.get_json()
    logout_token = data.get('logout_token')
    if not logout_token:
        return jsonify({"error": "Missing logout_token"}), 400
        
    try:
        secret = current_app.config.get('CENTRAL_AUTH_CLIENT_SECRET') or current_app.config['SECRET_KEY']
        payload = jwt.decode(logout_token, secret, algorithms=['HS256'])
        user_id = payload.get('sub')
        if not user_id:
            return jsonify({"error": "Invalid token"}), 400

        user_sessions = UserSSOSession.query.filter_by(user_id=user_id).all()
        session_ids = [s.session_id for s in user_sessions]
        if session_ids:
            db.session.execute(db.text("DELETE FROM sessions WHERE session_id IN :ids"), {"ids": tuple(session_ids)})
            UserSSOSession.query.filter(UserSSOSession.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.session.commit()
        return jsonify({"status": "success", "invalidated": len(session_ids)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- INTERNAL SSO SYNC API (ROOT LEVEL) ---

@internal_sync_bp.route('/api/sso-internal/user-list', methods=['POST'])
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

@internal_sync_bp.route('/api/sso-internal/link-user', methods=['POST'])
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

    if is_admin_sync:
        target_user = User.query.get(1)
        if target_user:
            # Collision Handling: If email or username is already taken by ANOTHER user
            if email:
                other_with_email = User.query.filter(User.email == email, User.user_id != 1).first()
                if other_with_email:
                    current_app.logger.warning(f"Sync Conflict: Email {email} taken by User {other_with_email.user_id}. Renaming existing user.")
                    other_with_email.email = f"{email}_old_{int(time.time())}"
            
            if username:
                other_with_username = User.query.filter(User.username == username, User.user_id != 1).first()
                if other_with_username:
                    current_app.logger.warning(f"Sync Conflict: Username {username} taken by User {other_with_username.user_id}. Renaming existing user.")
                    other_with_username.username = f"{username}_old_{int(time.time())}"
            
            if ca_id:
                other_with_ca = User.query.filter(User.central_auth_id == ca_id, User.user_id != 1).first()
                if other_with_ca:
                    current_app.logger.warning(f"Sync Conflict: CA ID {ca_id} taken by User {other_with_ca.user_id}. Detaching existing user.")
                    other_with_ca.central_auth_id = None

            if target_user.central_auth_id and target_user.central_auth_id != ca_id:
                current_app.logger.warning(f"Admin takeover: Overwriting central_auth_id {target_user.central_auth_id} with {ca_id} for local ID 1")
            target_user.username = username or target_user.username
            target_user.email = email or target_user.email
            if hasattr(target_user, 'full_name'):
                target_user.full_name = full_name or target_user.full_name
            target_user.central_auth_id = ca_id
            db.session.commit()
            return jsonify({"status": "success", "message": f"Admin identity pushed back to local ID 1 ({target_user.username})"}), 200

    if not target_user:
        target_user = User.query.filter_by(email=email).first()
    
    if not target_user and not is_admin_sync:
        target_user = User.query.filter_by(username=username).first()

    if target_user:
        target_user.central_auth_id = ca_id
        if full_name and hasattr(target_user, 'full_name'):
            target_user.full_name = full_name
        db.session.commit()
        return jsonify({"status": "success", "message": f"User {target_user.username} linked to CentralAuth ID {ca_id}"}), 200
    
    return jsonify({"error": "User not found for linking"}), 404

@internal_sync_bp.route('/api/sso-internal/delete-user', methods=['POST'])
def internal_delete_user():
    """Delete a user from this app's database."""
    secret = request.headers.get('X-Client-Secret')
    if secret != current_app.config.get('CENTRAL_AUTH_CLIENT_SECRET'):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    
    user = None
    if email and email != "null":
        user = User.query.filter_by(email=email).first()
    if not user and username and username != "null":
        user = User.query.filter_by(username=username).first()
        
    if not user:
        return jsonify({"error": f"User {username or email} not found"}), 404
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "ok", "message": f"Deleted {user.username}"}), 200

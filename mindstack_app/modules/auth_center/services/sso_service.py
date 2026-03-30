from flask import current_app
from mindstack_app.core.extensions import db
from mindstack_app.models import AppSettings
from mindstack_app.modules.auth.models import User, UserSession
from .central_auth_client import CentralAuthClient

class SSOService:
    """
    Dedicated service for managing CentralAuth SSO integration.
    """

    @staticmethod
    def get_config(key: str, default=None):
        try:
            return AppSettings.get(key, default)
        except:
            return default

    @staticmethod
    def get_client():
        api_url = SSOService.get_config('CENTRAL_AUTH_API_URL')
        web_url = SSOService.get_config('CENTRAL_SSO_WEB_URL', api_url)
        client_id = SSOService.get_config('CENTRAL_AUTH_CLIENT_ID')
        client_secret = SSOService.get_config('CENTRAL_AUTH_CLIENT_SECRET')
        return CentralAuthClient(api_url=api_url, web_url=web_url, client_id=client_id, client_secret=client_secret)

    @staticmethod
    def handle_callback(code):
        """
        Exchange the authorization code for tokens and provision/sync user.
        """
        client = SSOService.get_client()
        
        # 1. Exchange code for tokens (V2 Flow)
        token_data = client.exchange_code_for_token(code)
        if not token_data or 'access_token' not in token_data:
            current_app.logger.error("SSO Code exchange failed: No access_token returned")
            return None
            
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token')
        
        # 2. Verify token and get user payload
        user_payload = client.verify_token(access_token)
        if not user_payload:
            return None
            
        # 3. Store tokens in session for future API calls or refresh
        from flask import session
        session['sso_access_token'] = access_token
        if refresh_token:
            session['sso_refresh_token'] = refresh_token
            
        # 4. Provision local shadow user
        return SSOService.provision_user(user_payload)

    @staticmethod
    def provision_user(user_payload):
        """
        JIT Provisioning/Syncing logic for Central SSO users.
        """
        central_id = user_payload.get('id')
        email = user_payload.get('email')
        
        # 1. Lookup existing user by central_id or email
        user = User.query.filter(
            (User.central_auth_id == central_id) | (User.email == email)
        ).first()
        
        if user:
            # Update/Sync data
            user.central_auth_id = central_id
            user.email = email
            user.full_name = user_payload.get('full_name', user.full_name)
            user.avatar_url = user_payload.get('avatar_url', user.avatar_url)
            db.session.commit()
            return user
        else:
            # Create Shadow Record
            username = user_payload.get('username') or email.split('@')[0]
            if User.query.filter_by(username=username).first():
                suffix = str(central_id)[:6] if central_id else 'ext'
                username = f"{username}_{suffix}"
                
            user = User(
                username=username,
                email=email,
                full_name=user_payload.get('full_name'),
                avatar_url=user_payload.get('avatar_url'),
                central_auth_id=central_id,
                user_role=User.ROLE_USER
            )
            
            import uuid
            user.set_password(str(uuid.uuid4()))
            
            db.session.add(user)
            db.session.flush()
            
            user_session = UserSession(user_id=user.user_id)
            db.session.add(user_session)
            db.session.commit()
            return user

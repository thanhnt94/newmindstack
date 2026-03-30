import requests
from flask import current_app

class CentralAuthClient:
    """
    A reusable client for CentralAuth Single Sign-On.
    This class handles the core handshake and API calls to the identity provider.
    """

    def __init__(self, api_url, web_url=None, client_id=None, client_secret=None):
        self.api_url = api_url.rstrip('/') if api_url else None
        self.web_url = web_url.rstrip('/') if web_url else self.api_url
        self.client_id = client_id
        self.client_secret = client_secret

    def get_login_url(self, callback_url):
        """Generates the redirect URL for the CentralAuth login page."""
        if not self.web_url:
            return None
        
        connector = '&' if '?' in self.web_url else '?'
        return f"{self.web_url}/api/auth/login{connector}return_to={callback_url}"

    def check_health(self):
        """Checks if the CentralAuth server is reachable."""
        if not self.api_url:
            return False
        try:
            response = requests.get(f"{self.api_url}/api/auth/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def verify_token(self, token):
        """
        Verifies an SSO token and returns user information.
        Returns: User payload (dict) or None.
        """
        if not self.api_url:
            return None
            
        try:
            response = requests.get(
                f"{self.api_url}/api/auth/verify-token",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('user')
        except requests.exceptions.RequestException as e:
            if current_app:
                current_app.logger.error(f"CentralAuth token verification failed: {e}")
            
        return None

    def authenticate_credentials(self, username_or_email, password):
        """
        Performs direct credential authentication (Proxy Login).
        Returns: User payload (dict) or None.
        """
        if not self.api_url:
            return None
            
        try:
            response = requests.post(
                f"{self.api_url}/api/auth/login", 
                json={"email": username_or_email, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('user')
        except requests.exceptions.RequestException as e:
            if current_app:
                current_app.logger.warning(f"CentralAuth proxy login failed: {e}")
        
        return None

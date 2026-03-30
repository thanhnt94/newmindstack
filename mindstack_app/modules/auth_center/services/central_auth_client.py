import requests
from flask import current_app

class CentralAuthClient:
    """
    A reusable client for CentralAuth Single Sign-On.
    This class handles the core handshake and API calls to the identity provider.
    """

    def __init__(self, api_url, web_url=None, client_id=None, client_secret=None):
        # Robust URL cleaning: remove common suffixes if the user accidentally included them
        def clean_url(url):
            if not url: return None
            cleaned = url.rstrip('/')
            for suffix in ['/api/auth/login', '/api/auth/verify-token', '/api/auth']:
                if cleaned.endswith(suffix):
                    cleaned = cleaned[:len(cleaned)-len(suffix)]
            return cleaned.rstrip('/')

        self.api_url = clean_url(api_url)
        self.web_url = clean_url(web_url or api_url)
        self.client_id = client_id
        self.client_secret = client_secret

    def get_login_url(self, callback_url):
        """Generates the redirect URL for the CentralAuth login page."""
        if not self.web_url:
            return None
        
        connector = '&' if '?' in self.web_url else '?'
        return f"{self.web_url}/api/auth/login{connector}return_to={callback_url}&client_id={self.client_id}"

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
                current_app.logger.info(f"SSO verification error: {e}")
            
        return None

    def exchange_code_for_token(self, code):
        """
        Exchanges an authorization code for an access/refresh token pair. (V2 Flow)
        """
        if not self.api_url or not self.client_id or not self.client_secret:
            return None

        try:
            response = requests.post(
                f"{self.api_url}/api/auth/token",
                json={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            if current_app:
                current_app.logger.error(f"CentralAuth code exchange failed: {e}")

        return None

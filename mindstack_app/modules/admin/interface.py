# File: mindstack_app/modules/admin/interface.py
from mindstack_app.models import AppSettings

class AdminInterface:
    @staticmethod
    def get_setting(key: str, default=None):
        return AppSettings.get(key, default)

    @staticmethod
    def set_setting(key: str, value, category='system', user_id=None):
        AppSettings.set(key, value, category=category, user_id=user_id)

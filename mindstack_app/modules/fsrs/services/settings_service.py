# modules/fsrs/services/settings_service.py
from mindstack_app.models import AppSettings, db
from ..config import FSRSDefaultConfig

class FSRSSettingsService:
    @staticmethod
    def get_parameters():
        return {
            'FSRS_DESIRED_RETENTION': AppSettings.get('FSRS_DESIRED_RETENTION', FSRSDefaultConfig.FSRS_DESIRED_RETENTION),
            'FSRS_MAX_INTERVAL': AppSettings.get('FSRS_MAX_INTERVAL', FSRSDefaultConfig.FSRS_MAX_INTERVAL),
            'FSRS_ENABLE_FUZZ': AppSettings.get('FSRS_ENABLE_FUZZ', FSRSDefaultConfig.FSRS_ENABLE_FUZZ),
            'FSRS_GLOBAL_WEIGHTS': AppSettings.get('FSRS_GLOBAL_WEIGHTS', FSRSDefaultConfig.FSRS_GLOBAL_WEIGHTS),
        }

    @staticmethod
    def get_defaults():
        return {
            'FSRS_DESIRED_RETENTION': FSRSDefaultConfig.FSRS_DESIRED_RETENTION,
            'FSRS_MAX_INTERVAL': FSRSDefaultConfig.FSRS_MAX_INTERVAL,
            'FSRS_ENABLE_FUZZ': FSRSDefaultConfig.FSRS_ENABLE_FUZZ,
            'FSRS_GLOBAL_WEIGHTS': FSRSDefaultConfig.FSRS_GLOBAL_WEIGHTS
        }

    @staticmethod
    def save_parameters(data):
        for key, value in data.items():
            AppSettings.set(key, value, category='fsrs')
        db.session.commit()

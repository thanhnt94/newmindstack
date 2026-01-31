# modules/fsrs/interface.py
from .services.settings_service import FSRSSettingsService

class FSRSInterface:
    """
    Interface để tính toán thuật toán FSRS.
    """
    
    @staticmethod
    def get_fsrs_parameters():
        """Lấy bộ tham số thuật toán hiện tại."""
        return FSRSSettingsService.get_parameters()

    @staticmethod
    def calculate_next_review(stability, difficulty, rating):
        """
        Gọi Engine tính toán (Thực tế sẽ gọi sang .engine.processor).
        """
        # from .engine.processor import FSRSEngine
        # return FSRSEngine.calculate(...)
        pass

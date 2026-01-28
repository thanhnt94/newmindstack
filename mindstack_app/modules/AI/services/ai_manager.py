# File: mindstack_app/modules/ai_services/service_manager.py
# Phiên bản: 1.1
# MỤC ĐÍCH: Quản lý và cung cấp instance của AI Service dựa trên cấu hình hệ thống.

import threading
from flask import current_app
from mindstack_app.models import AppSettings
from ..logics.engines.gemini_client import GeminiClient
from ..logics.engines.huggingface_client import HuggingFaceClient
from ..logics.engines.hybrid_client import HybridAIClient

class AIServiceManager:
    _instance = None
    _lock = threading.Lock()
    _current_provider = None
    _current_gemini_model = None
    _current_hf_model = None
    _service_instance = None

    @classmethod
    def get_service(cls, app_context):
        """
        Mô tả: Factory method trả về instance của Hybrid AI Service.
        Luôn trả về HybridAIClient để hỗ trợ fallback tự động.
        """
        try:
            # Lấy cấu hình ưu tiên
            primary_provider = AppSettings.get('AI_PROVIDER', 'gemini')
            
            # Lấy model cho từng loại
            gemini_model = AppSettings.get('GEMINI_MODEL', 'gemini-2.0-flash-lite-001')
            hf_model = AppSettings.get('HUGGINGFACE_MODEL', 'google/gemma-7b-it')

            with cls._lock:
                # Kiểm tra xem có cần khởi tạo lại không (nếu cấu hình thay đổi)
                if (cls._service_instance is None or 
                    cls._current_provider != primary_provider or 
                    cls._current_gemini_model != gemini_model or
                    cls._current_hf_model != hf_model):
                    
                    current_app.logger.info(
                        f"AIServiceManager: Khởi tạo HybridAIClient. "
                        f"Ưu tiên: {primary_provider}. Gemini: {gemini_model}, HF: {hf_model}"
                    )
                    
                    cls._service_instance = HybridAIClient(
                        app_context, 
                        primary_provider=primary_provider,
                        gemini_model=gemini_model,
                        hf_model=hf_model
                    )
                    
                    cls._current_provider = primary_provider
                    cls._current_gemini_model = gemini_model
                    cls._current_hf_model = hf_model
            
            return cls._service_instance

        except Exception as e:
            current_app.logger.error(f"AIServiceManager: Lỗi khi khởi tạo service: {e}")
            # Fallback an toàn cực đoan
            return GeminiClient(app_context)

def get_ai_service():
    """
    Hàm helper để lấy AI service hiện tại.
    """
    from mindstack_app import app
    return AIServiceManager.get_service(app.app_context())

from flask import current_app
from .gemini_client import GeminiClient
from .huggingface_client import HuggingFaceClient

class HybridAIClient:
    """
    Mô tả: Client thông minh tự động chuyển đổi giữa các nhà cung cấp AI.
    Nó sẽ thử lần lượt từng provider trong danh sách ưu tiên.
    """
    def __init__(self, app_context, primary_provider='gemini', gemini_model=None, hf_model=None):
        self.app_context = app_context
        self.primary_provider = primary_provider
        
        # Khởi tạo các client con
        # Lưu ý: Việc khởi tạo client con thường nhẹ (chỉ gán biến), kết nối thật sự xảy ra khi gọi hàm
        self.gemini_client = GeminiClient(app_context, model_name=gemini_model)
        self.hf_client = HuggingFaceClient(app_context, model_name=hf_model)
        
        # Xác định thứ tự ưu tiên
        if primary_provider == 'huggingface':
            self.execution_order = [
                ('huggingface', self.hf_client),
                ('gemini', self.gemini_client)
            ]
        else:
            # Mặc định ưu tiên Gemini
            self.execution_order = [
                ('gemini', self.gemini_client),
                ('huggingface', self.hf_client)
            ]

    def generate_content(self, prompt, item_info="N/A"):
        """
        Mô tả: Thử tạo nội dung với provider chính, nếu thất bại sẽ thử provider phụ.
        """
        errors = []
        
        for provider_name, client in self.execution_order:
            current_app.logger.info(f"HybridAI: Đang thử tạo nội dung bằng {provider_name}...")
            
            try:
                # Gọi hàm generate_content của từng client con
                success, result = client.generate_content(prompt, item_info)
                
                if success:
                    current_app.logger.info(f"HybridAI: Thành công với {provider_name}.")
                    return True, result
                else:
                    error_msg = f"{provider_name} thất bại: {result}"
                    errors.append(error_msg)
                    current_app.logger.warning(f"HybridAI: {error_msg}. Đang chuyển sang provider tiếp theo...")
            
            except Exception as e:
                error_msg = f"{provider_name} gặp lỗi nghiêm trọng: {str(e)}"
                errors.append(error_msg)
                current_app.logger.error(f"HybridAI: {error_msg}", exc_info=True)
                continue

        # Nếu chạy hết vòng lặp mà không return, tức là tất cả đều thất bại
        final_error = " || ".join(errors)
        return False, f"Tất cả các nguồn AI đều thất bại. Chi tiết: {final_error}"

    # Các hàm tiện ích khác (nếu cần) có thể delegate cho primary client
    @staticmethod
    def get_available_models():
        # Hàm này hơi khó vì mỗi provider có list riêng.
        # Tạm thời trả về list của provider mặc định hoặc list rỗng.
        return {'success': False, 'message': 'Hybrid client không hỗ trợ liệt kê model chung.'}

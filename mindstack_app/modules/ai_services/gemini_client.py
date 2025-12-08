# File: mindstack_app/modules/ai_services/gemini_client.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Tích hợp ApiKeyManager dùng chung và hỗ trợ chọn model động.

import time
import threading
from flask import current_app
from .key_manager import ApiKeyManager

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    genai = None

class GeminiClient:
    """
    Mô tả: Lớp client để quản lý kết nối và gửi yêu cầu đến Gemini API,
    sử dụng ApiKeyManager để tăng độ tin cậy.
    """
    def __init__(self, app_context, model_name='gemini-2.0-flash-lite-001'):
        """
        Mô tả: Khởi tạo Gemini Client.
        Args:
            app_context: Flask application context.
            model_name (str): Tên model Gemini cần dùng.
        """
        if not genai:
            raise ImportError("Thư viện 'google-generativeai' chưa được cài đặt.")
        
        self.app_context = app_context
        # Khởi tạo manager với provider là 'gemini'
        self.api_key_manager = ApiKeyManager(provider='gemini')
        self.model_name = model_name
        current_app.logger.info(f"Gemini Client đã được khởi tạo với model '{self.model_name}'.")

    def generate_content(self, prompt, item_info="N/A"):
        """
        Mô tả: Gửi một prompt đến Gemini API và nhận lại nội dung.

        Trả về tuple (success: bool, message: str) để phân biệt rõ giữa kết quả
        hợp lệ và thông báo lỗi.
        """
        max_retries = 5
        last_error_msg = None
        previous_key_id = None

        for attempt in range(max_retries):
            with self.app_context:
                key_id, key_value = self.api_key_manager.get_key()

            if not key_id:
                error_msg = "Tất cả các API key (Gemini) đều đã cạn kiệt hoặc không hợp lệ."
                current_app.logger.error(f"GeminiClient: {error_msg}")
                return False, error_msg

            current_app.logger.info(
                f"GeminiClient: Sử dụng API key ID {key_id} cho {item_info} (Lần thử {attempt + 1})"
            )

            try:
                genai.configure(api_key=key_value)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)

                if response.parts:
                    return True, response.text

                feedback = response.prompt_feedback
                last_error_msg = f"AI không thể tạo nội dung. Phản hồi từ Google: {feedback}"
                current_app.logger.warning(
                    f"GeminiClient: Phản hồi trống cho {item_info}. {last_error_msg}"
                )
            except google_exceptions.PermissionDenied as e:
                current_app.logger.error(
                    f"GeminiClient: Lỗi PermissionDenied với key ID {key_id}: {e}. Đánh dấu là cạn kiệt."
                )
                with self.app_context:
                    self.api_key_manager.mark_key_as_exhausted(key_id)
                previous_key_id = key_id
                continue
            except google_exceptions.ResourceExhausted as e:
                # Chiến lược mới: Fail Fast & Round Robin
                # Lỗi này là tạm thời (Quota), KHÔNG được đánh dấu key là hỏng vĩnh viễn.
                
                if previous_key_id == key_id:
                    # Đã quay vòng lại key cũ -> Nghĩa là tất cả key đều đang bị rate limit.
                    # Dừng ngay lập tức, không spam API nữa.
                    error_msg = "Tạm thời hết hạn mức Quota trên tất cả các API Key. Vui lòng thử lại sau ít phút."
                    current_app.logger.warning(f"GeminiClient: {error_msg}")
                    return False, error_msg
                
                # Nếu chưa quay vòng lại, chỉ đơn giản là thử key tiếp theo ngay lập tức.
                current_app.logger.warning(
                    f"GeminiClient: Key ID {key_id} bị 429 (ResourceExhausted). Đang thử key tiếp theo..."
                )
                previous_key_id = key_id
                # Gọi force_refresh để đảm bảo ta có danh sách mới nhất nếu có key mới thêm vào
                self.api_key_manager.force_refresh() 
                continue
            except google_exceptions.ServiceUnavailable as e:
                current_app.logger.warning(
                    f"GeminiClient: ServiceUnavailable (503). Đang thử lại..."
                )
                time.sleep(2)
                previous_key_id = key_id
                continue
            except Exception as e:
                last_error_msg = f"Lỗi server khi gọi AI: {e}"
                current_app.logger.error(
                    f"GeminiClient: Lỗi khi gọi Gemini API cho {item_info} với key ID {key_id}: {e}",
                    exc_info=True,
                )
                break

        final_error_msg = last_error_msg or "Đã thử tất cả API key nhưng đều thất bại."
        current_app.logger.critical(f"GeminiClient: {final_error_msg}")
        return False, final_error_msg

    @staticmethod
    def get_available_models():
        """
        Mô tả: Lấy danh sách các model khả dụng từ Google API.
        Sử dụng một API key bất kỳ đang hoạt động để truy vấn.
        """
        if not genai:
            return {'success': False, 'message': "Thư viện google-generativeai chưa được cài đặt."}

        try:
            # Tạo manager tạm để lấy 1 key
            temp_manager = ApiKeyManager(provider='gemini')
            key_id, key_value = temp_manager.get_key()

            if not key_value:
                return {'success': False, 'message': "Không tìm thấy API Key nào khả dụng để tải danh sách model."}

            genai.configure(api_key=key_value)
            
            models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    # Clean up the name (remove 'models/' prefix if present)
                    model_id = m.name.replace('models/', '')
                    models.append({
                        'id': model_id,
                        'display_name': m.display_name,
                        'description': m.description
                    })
            
            # Sắp xếp: Flash/Lite lên đầu, Pro tiếp theo
            def sort_key(m):
                name = m['id'].lower()
                if 'flash' in name and 'lite' in name: return 0
                if 'flash' in name: return 1
                if 'pro' in name: return 2
                return 3
            
            models.sort(key=sort_key)
            
            return {'success': True, 'models': models}
            
        except Exception as e:
            current_app.logger.error(f"Lỗi khi lấy danh sách model: {e}")
            return {'success': False, 'message': f"Lỗi kết nối Google: {str(e)}"}

# Biến toàn cục để lưu trữ instance của client
gemini_client_instance = None
gemini_client_lock = threading.Lock()

def get_gemini_client():
    """
    DEPRECATED: Sử dụng service_manager.get_ai_service() thay thế.
    Giữ lại để tương thích ngược tạm thời.
    """
    global gemini_client_instance
    with gemini_client_lock:
        if gemini_client_instance is None:
            try:
                from ... import app
                gemini_client_instance = GeminiClient(app.app_context())
            except (ImportError, ValueError) as e:
                current_app.logger.error(f"Không thể khởi tạo Gemini Client: {e}")
                gemini_client_instance = None
    return gemini_client_instance

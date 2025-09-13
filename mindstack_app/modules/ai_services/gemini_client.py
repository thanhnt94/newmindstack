# File: mindstack_app/modules/ai_services/gemini_client.py
# Phiên bản: 2.1
# MỤC ĐÍCH: Khắc phục lỗi DetachedInstanceError.
# ĐÃ SỬA: Thay đổi logic để không truyền đối tượng SQLAlchemy ra ngoài session của nó.
#          Hàm get_key giờ sẽ trả về id và value thay vì cả object.
#          Hàm mark_key_as_exhausted sẽ nhận key_id để tự truy vấn.

import time
import threading
from flask import current_app
from ...db_instance import db
from ...models import ApiKey

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    genai = None

class ApiKeyManager:
    """
    Mô tả: Quản lý việc lấy và xoay vòng các API key từ database.
    Hoạt động bên trong application context của Flask.
    """
    def __init__(self):
        self.key_ids = []
        self.lock = threading.Lock()
        self.keys_loaded = False

    def _load_keys(self):
        """
        Mô tả: Tải lại danh sách ID của các API key hợp lệ từ database.
        Hàm này phải được gọi bên trong một application context.
        """
        try:
            self.key_ids = [
                k.key_id for k in ApiKey.query.filter_by(
                    is_active=True, is_exhausted=False
                ).order_by(ApiKey.last_used_timestamp.asc()).all()
            ]
            self.keys_loaded = True
            current_app.logger.info(f"ApiKeyManager: Đã tải {len(self.key_ids)} ID của API key hợp lệ.")
        except Exception as e:
            current_app.logger.error(f"ApiKeyManager: Lỗi khi tải API keys từ database: {e}", exc_info=True)
            self.key_ids = []

    def get_key(self):
        """
        Mô tả: Lấy ID và giá trị của một API key khả dụng để sử dụng.
        Returns:
            tuple: (key_id, key_value) hoặc (None, None) nếu hết key.
        """
        with self.lock:
            while True:
                if not self.keys_loaded or not self.key_ids:
                    self._load_keys()
                    if not self.key_ids:
                        current_app.logger.warning("ApiKeyManager: Không còn API key nào khả dụng.")
                        return None, None
                
                if not self.key_ids:
                    return None, None

                key_id = self.key_ids.pop(0)
                
                try:
                    key_obj = ApiKey.query.get(key_id)
                    
                    if key_obj and key_obj.is_active and not key_obj.is_exhausted:
                        key_obj.last_used_timestamp = db.func.now()
                        db.session.commit()
                        # Trả về giá trị và ID, không trả về object
                        return key_obj.key_id, key_obj.key_value
                    else:
                        current_app.logger.warning(f"ApiKeyManager: Key ID {key_id} không còn hợp lệ, bỏ qua.")
                        continue
                except Exception as e:
                    current_app.logger.error(f"ApiKeyManager: Lỗi khi lấy và cập nhật key_id {key_id}: {e}")
                    db.session.rollback()
                    continue

    def mark_key_as_exhausted(self, key_id):
        """
        Mô tả: Đánh dấu một API key là đã cạn kiệt dựa trên ID của nó.
        """
        with self.lock:
            try:
                key_obj = ApiKey.query.get(key_id)
                if key_obj:
                    key_obj.is_exhausted = True
                    db.session.commit()
                    current_app.logger.warning(f"ApiKeyManager: Đã đánh dấu API key ID {key_obj.key_id} là đã cạn kiệt.")
            except Exception as e:
                current_app.logger.error(f"ApiKeyManager: Lỗi khi đánh dấu key ID {key_id} là cạn kiệt: {e}")
                db.session.rollback()

class GeminiClient:
    """
    Mô tả: Lớp client để quản lý kết nối và gửi yêu cầu đến Gemini API,
    sử dụng ApiKeyManager để tăng độ tin cậy.
    """
    def __init__(self, app_context):
        """
        Mô tả: Khởi tạo Gemini Client.
        """
        if not genai:
            raise ImportError("Thư viện 'google-generativeai' chưa được cài đặt.")
        
        self.app_context = app_context
        self.api_key_manager = ApiKeyManager()
        self.model_name = 'gemini-1.5-flash'
        current_app.logger.info(f"Gemini Client đã được khởi tạo với model '{self.model_name}'.")

    def generate_content(self, prompt, item_info="N/A"):
        """
        Mô tả: Gửi một prompt đến Gemini API và nhận lại nội dung.
        """
        max_retries = 5
        
        for attempt in range(max_retries):
            with self.app_context:
                key_id, key_value = self.api_key_manager.get_key()
            
            if not key_id:
                error_msg = "Tất cả các API key đều đã cạn kiệt hoặc không hợp lệ."
                current_app.logger.error(f"GeminiClient: {error_msg}")
                return error_msg

            current_app.logger.info(f"GeminiClient: Sử dụng API key ID {key_id} cho {item_info} (Lần thử {attempt + 1})")
            
            try:
                genai.configure(api_key=key_value)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)

                if response.parts:
                    return response.text
                else:
                    feedback = response.prompt_feedback
                    error_msg = f"AI không thể tạo nội dung. Phản hồi từ Google: {feedback}"
                    current_app.logger.warning(f"GeminiClient: Phản hồi trống cho {item_info}. {error_msg}")
                    return error_msg
            except google_exceptions.PermissionDenied as e:
                current_app.logger.error(f"GeminiClient: Lỗi PermissionDenied với key ID {key_id}: {e}. Đánh dấu là cạn kiệt.")
                with self.app_context:
                    self.api_key_manager.mark_key_as_exhausted(key_id)
                continue
            except Exception as e:
                error_msg = f"Lỗi server khi gọi AI: {e}"
                current_app.logger.error(f"GeminiClient: Lỗi khi gọi Gemini API cho {item_info} với key ID {key_id}: {e}", exc_info=True)
                return error_msg
                
        final_error_msg = "Đã thử tất cả API key nhưng đều thất bại."
        current_app.logger.critical(f"GeminiClient: {final_error_msg}")
        return final_error_msg

# Biến toàn cục để lưu trữ instance của client
gemini_client_instance = None
gemini_client_lock = threading.Lock()

def get_gemini_client():
    """
    Mô tả: Hàm factory để đảm bảo chỉ có một instance của GeminiClient được tạo ra cho toàn ứng dụng.
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
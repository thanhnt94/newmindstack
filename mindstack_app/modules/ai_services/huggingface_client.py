# File: mindstack_app/modules/ai_services/huggingface_client.py
# Phiên bản: 1.0
# MỤC ĐÍCH: Client kết nối với Hugging Face Inference API.

import time
from flask import current_app
from .key_manager import ApiKeyManager

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

class HuggingFaceClient:
    """
    Mô tả: Lớp client để quản lý kết nối và gửi yêu cầu đến Hugging Face Inference API.
    """
    def __init__(self, app_context, model_name='google/gemma-7b-it'):
        """
        Mô tả: Khởi tạo Hugging Face Client.
        Args:
            app_context: Flask application context.
            model_name (str): Tên model HF cần dùng (Repo ID).
        """
        if not InferenceClient:
            raise ImportError("Thư viện 'huggingface_hub' chưa được cài đặt.")
        
        self.app_context = app_context
        self.api_key_manager = ApiKeyManager(provider='huggingface')
        self.model_name = model_name
        current_app.logger.info(f"HuggingFace Client đã được khởi tạo với model '{self.model_name}'.")

    def generate_content(self, prompt, item_info="N/A"):
        """
        Mô tả: Gửi một prompt đến HF Inference API và nhận lại nội dung.
        """
        max_retries = 3
        last_error_msg = None

        for attempt in range(max_retries):
            with self.app_context:
                key_id, key_value = self.api_key_manager.get_key()

            if not key_id:
                error_msg = "Tất cả các API key (HuggingFace) đều đã cạn kiệt hoặc không hợp lệ."
                current_app.logger.error(f"HuggingFaceClient: {error_msg}")
                return False, error_msg

            current_app.logger.info(
                f"HuggingFaceClient: Sử dụng API key ID {key_id} cho {item_info} (Lần thử {attempt + 1})"
            )

            try:
                # FIX: Dùng URL trực tiếp để tránh lỗi StopIteration trong cơ chế auto-routing của thư viện
                model_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
                client = InferenceClient(model=model_url, token=key_value)
                
                # Cấu hình tin nhắn cho Chat Model
                messages = [{"role": "user", "content": prompt}]

                # Thử dùng chat_completion API
                try:
                    chat_response = client.chat_completion(
                        messages, 
                        max_tokens=1500,
                        temperature=0.7
                    )
                    # Lấy nội dung trả về
                    if chat_response.choices and chat_response.choices[0].message:
                        return True, chat_response.choices[0].message.content
                except (AttributeError, StopIteration, ValueError, Exception) as e:
                    # Fallback nếu chat thất bại (hoặc model không hỗ trợ chat qua endpoint này)
                    # Lưu ý: Exception ở đây bắt rộng hơn để bắt cả lỗi HTTP 404/500 từ requests bên dưới
                    current_app.logger.info(f"HuggingFaceClient: Chat completion lỗi ({str(e)}), chuyển sang text_generation.")
                    
                    formatted_prompt = f"User: {prompt}\n\nAssistant:"
                    
                    response = client.text_generation(
                        formatted_prompt, 
                        max_new_tokens=1024,
                        temperature=0.7
                    )
                    if response:
                        return True, response

                last_error_msg = "AI trả về phản hồi trống."
                current_app.logger.warning(
                    f"HuggingFaceClient: Phản hồi trống cho {item_info}."
                )

            except Exception as e:
                error_str = str(e)
                last_error_msg = f"Lỗi gọi HF API: {error_str}"
                
                # Xử lý các lỗi thường gặp
                if "401" in error_str or "Unauthorized" in error_str:
                    current_app.logger.error(
                        f"HuggingFaceClient: Key ID {key_id} không hợp lệ (401). Đánh dấu cạn kiệt."
                    )
                    with self.app_context:
                        self.api_key_manager.mark_key_as_exhausted(key_id)
                elif "429" in error_str: # Rate limit
                    current_app.logger.warning(
                        f"HuggingFaceClient: Rate limit (429) với key ID {key_id}. Đổi key..."
                    )
                    time.sleep(2)
                    continue
                elif "503" in error_str or "Model is loading" in error_str:
                     # Cold start: Model đang được tải lên GPU, cần đợi lâu hơn
                     wait_time = 20
                     current_app.logger.warning(
                        f"HuggingFaceClient: Model '{self.model_name}' đang khởi động (cold start). Đợi {wait_time}s rồi thử lại..."
                    )
                     time.sleep(wait_time)
                     # Giảm attempt đi 1 để không bị tính là thất bại (cho phép thử lại nhiều lần cho lỗi này)
                     # Tuy nhiên trong vòng for range() không thể giảm biến chạy, ta có thể dùng continue
                     # nhưng cần cẩn thận lặp vô hạn. Ở đây ta chấp nhận mất 1 attempt nhưng đợi lâu.
                     continue
                
                current_app.logger.error(
                    f"HuggingFaceClient: Lỗi không xác định với key ID {key_id}: {e}",
                    exc_info=True
                )
                continue

        final_error_msg = last_error_msg or "Đã thử các API key nhưng thất bại."
        current_app.logger.critical(f"HuggingFaceClient: {final_error_msg}")
        return False, final_error_msg

    @staticmethod
    def get_available_models():
        """
        Mô tả: Lấy danh sách top model text-generation từ Hugging Face Hub.
        """
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            
            # Lấy top 30 model text-generation được tải nhiều nhất
            models = api.list_models(
                filter="text-generation",
                sort="downloads",
                direction=-1,
                limit=30
            )
            
            result = []
            for m in models:
                # Bỏ qua các model quá lạ hoặc không phải tiếng Anh/Code (lọc sơ bộ)
                result.append({
                    'id': m.modelId,
                    'display_name': m.modelId,
                    'description': f"Downloads: {m.downloads}"
                })
            
            return {'success': True, 'models': result}
        except ImportError:
            return {'success': False, 'message': "Thư viện 'huggingface_hub' chưa cài đặt đầy đủ."}
        except Exception as e:
            current_app.logger.error(f"Lỗi lấy model HF: {e}")
            return {'success': False, 'message': f"Lỗi kết nối Hugging Face: {str(e)}"}

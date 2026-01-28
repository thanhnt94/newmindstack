import threading
from flask import current_app
from mindstack_app.db_instance import db
from mindstack_app.models import ApiKey

class ApiKeyManager:
    """
    Mô tả: Quản lý việc lấy và xoay vòng các API key từ database theo nhà cung cấp (provider).
    Hoạt động bên trong application context của Flask.
    """
    def __init__(self, provider='gemini'):
        self.provider = provider
        self.key_ids = []
        self.lock = threading.Lock()
        self.keys_loaded = False

    def _load_keys(self):
        """
        Mô tả: Tải lại danh sách ID của các API key hợp lệ từ database cho provider cụ thể.
        Hàm này phải được gọi bên trong một application context.
        """
        try:
            # Refresh session to ensure we get latest data
            db.session.expire_all()
            
            keys = ApiKey.query.filter_by(
                provider=self.provider,
                is_active=True, 
                is_exhausted=False
            ).order_by(ApiKey.last_used_timestamp.asc()).all()
            
            self.key_ids = [k.key_id for k in keys]
            self.keys_loaded = True
            
            key_list_str = ", ".join(str(k) for k in self.key_ids)
            current_app.logger.info(f"ApiKeyManager ({self.provider}): Đã tải {len(self.key_ids)} key khả dụng. IDs: [{key_list_str}]")
            
            if not self.key_ids:
                # Debug: Check if there are ANY keys at all
                total = ApiKey.query.filter_by(provider=self.provider).count()
                active = ApiKey.query.filter_by(provider=self.provider, is_active=True).count()
                current_app.logger.warning(f"DEBUG: Tổng số key: {total}, Active: {active}. Nhưng không có key nào khả dụng (có thể do exhausted=True).")

        except Exception as e:
            current_app.logger.error(f"ApiKeyManager ({self.provider}): Lỗi khi tải API keys từ database: {e}", exc_info=True)
            self.key_ids = []

    def force_refresh(self):
        """
        Mô tả: Ép buộc tải lại danh sách key từ database vào lần gọi get_key tiếp theo.
        """
        with self.lock:
            self.keys_loaded = False
            self.key_ids = []
            current_app.logger.info(f"ApiKeyManager ({self.provider}): Đã nhận yêu cầu làm mới danh sách key.")

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
                        current_app.logger.warning(f"ApiKeyManager ({self.provider}): Không còn API key nào khả dụng.")
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
                        current_app.logger.warning(f"ApiKeyManager ({self.provider}): Key ID {key_id} không còn hợp lệ, bỏ qua.")
                        continue
                except Exception as e:
                    current_app.logger.error(f"ApiKeyManager ({self.provider}): Lỗi khi lấy và cập nhật key_id {key_id}: {e}")
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
                    current_app.logger.warning(f"ApiKeyManager ({self.provider}): Đã đánh dấu API key ID {key_obj.key_id} là đã cạn kiệt.")
            except Exception as e:
                current_app.logger.error(f"ApiKeyManager ({self.provider}): Lỗi khi đánh dấu key ID {key_id} là cạn kiệt: {e}")
                db.session.rollback()

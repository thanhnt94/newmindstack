# 🧩 MindStack Module Architecture (v2.0)

## Overview
Modules trong MindStack được thiết kế theo nguyên lý **Modular Monolith**. Mục tiêu là đảm bảo tính cô lập (Isolation) cao nhất có thể, tránh phụ thuộc chéo (Circular Dependencies) và cho phép mở rộng tính năng mà không cần sửa đổi lõi (Open/Closed Principle).

---

## 📂 Cấu trúc Module Nâng cao

Một module "chuẩn" để đảm bảo tính tách biệt cần có các thành phần sau:

```
modules/my_module/
├── routes/              # Giao diện HTTP (Web/API)
├── services/            # Tầng xử lý nghiệp vụ (Business Logic)
├── logics/              # Các hàm xử lý thuần túy (Pure Functions)
├── events.py            # Event Handlers (Subscribers) cho các Signals
├── schemas.py           # DTOs (Data Transfer Objects) dùng Marshmallow/Pydantic
├── models.py            # Database Models riêng của module
├── constants.py         # Hằng số cấu hình module
└── __init__.py          # Đăng ký Blueprint & Integration hooks
```

---

## 📡 Cơ chế Giao tiếp: Signals (Events)

Để tránh Module A phải `import` Module B (gây phụ thuộc trực tiếp), MindStack sử dụng **Event-Driven Architecture** thông qua thư viện `blinker`.

### 1. Publisher (Người gửi)
Module gửi đi một thông báo khi có hành động xảy ra.
```python
# Trong modules/learning/services/session_service.py
from mindstack_app.core.signals import card_reviewed

card_reviewed.send(
    None, 
    user_id=user.id, 
    score_points=10,
    item_type='FLASHCARD'
)
```

### 2. Subscriber (Người nhận)
Module khác "lắng nghe" và thực hiện hành động tương ứng trong file `events.py`.
```python
# Trong modules/gamification/events.py
from mindstack_app.core.signals import card_reviewed

@card_reviewed.connect
def on_card_reviewed(sender, **kwargs):
    # Trao điểm thưởng mà không cần Module Learning biết về Module Gamification
    user_id = kwargs.get('user_id')
    points = kwargs.get('score_points')
    ScoreService.award_points(user_id, points)
```

**Các Signal Registry chính:** Xem tại `mindstack_app/core/signals.py`.

---

## 📦 Data Transfer Objects (DTOs) & Schemas

MindStack sử dụng `schemas.py` (thường là **Marshmallow**) để định nghĩa cấu trúc dữ liệu trao đổi.

### Tại sao dùng DTO?
1.  **Validation**: Kiểm tra tính hợp lệ của dữ liệu đầu vào.
2.  **Serialization**: Chuyển đổi Model (SQLAlchemy) sang JSON an toàn.
3.  **Decoupling**: Routes không làm việc trực tiếp với Model mà thông qua Schema, giúp ẩn đi các trường nhạy cảm hoặc logic DB phức tạp.

```python
# Trong modules/auth/schemas.py
from marshmallow import Schema, fields

class UserSchema(Schema):
    user_id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email()
```

---

## 🛠️ Quy tắc để Module "Thực sự Tách biệt"

### 1. Không import chéo (No Cross-Module Imports)
- **Sai**: `from mindstack_app.modules.gamification.models import Score` (trong module Learning).
- **Đúng**: Gửi một Signal và để module Gamification tự xử lý model của nó.

### 2. Dependency Injection (DI) gián tiếp
Nếu cần gọi một Service của module khác, hãy sử dụng **Service Registry** hoặc kiểm tra thông qua `module_registry.py`.

### 3. Database Isolation
Mỗi module nên quản lý các bảng của riêng nó. Nếu cần truy vấn dữ liệu từ bảng của module khác, hãy thực hiện qua Service Layer của module đó (hoặc qua API nội bộ) thay vì Join trực tiếp trong SQL nếu có thể.

### 4. Integration via `setup_module(app)`
Trong `__init__.py`, hàm `setup_module` được gọi bởi `bootstrap.py`. Đây là nơi để:
- Đăng ký Scheduler tasks cho riêng module.
- Khởi tạo các biến global của module.
- Đăng ký các bộ lắng nghe sự kiện (Subscribers).

---

## 📋 Checklist Phát triển Module
- [ ] Module có Blueprint được khai báo trong `__init__.py`?
- [ ] Các logic xử lý sự kiện từ module khác đã được đặt trong `events.py`?
- [ ] Dữ liệu trả về cho API đã được chuẩn hóa qua `schemas.py`?
- [ ] Đã kiểm tra không có `import` trực tiếp từ các module khác chưa? (Trừ các module hạ tầng như AI hoặc Notification).
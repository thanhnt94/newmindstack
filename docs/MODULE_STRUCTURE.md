Tài liệu này định nghĩa cấu trúc thư mục chuẩn và các quy tắc phụ thuộc (**dependency rules**) nghiêm ngặt để đảm bảo khả năng mở rộng (scalability) và bảo trì (maintainability) của hệ thống MindStack.

## 📁 1. Cấu trúc Thư mục Chuẩn (Standard Directory Tree)

Mỗi module trong hệ thống (ví dụ: `auth`, `fsrs`, `gamification`) **PHẢI** tuân thủ cấu trúc thư mục sau:

```text
mindstack_app/modules/{module_name}/
├── __init__.py           # Khởi tạo module, đăng ký Blueprint & Event Listeners
├── config.py             # Cấu hình mặc định (Default Config) & Hằng số
├── interface.py          # Cổng giao tiếp CÔNG KHAI (Public API) cho các module khác
├── models.py             # Định nghĩa Database Models (SQLAlchemy)
├── schemas.py            # Pydantic/Marshmallow Models (Data Transfer Objects - DTOs)
├── exceptions.py         # 🆕 Định nghĩa các lỗi nghiệp vụ riêng (Domain Exceptions)
├── events.py             # Nơi LẮNG NGHE sự kiện (Event Listeners) từ module khác
├── signals.py            # Nơi ĐỊNH NGHĨA sự kiện (Signal Definitions) module này phát ra
├── tasks.py              # 🆕 Các tác vụ chạy nền (Celery Tasks / Async Jobs)
├── routes/               # Tầng giao tiếp (Presentation Layer)
│   ├── __init__.py
│   ├── api.py            # JSON Endpoints (REST API)
│   └── views.py          # HTML Endpoints (Jinja2 Templates)
├── services/             # Tầng quản lý & điều phối (Orchestrator Layer - Stateful)
│   ├── __init__.py
│   └── {name}_service.py # Logic nghiệp vụ có tương tác Database
├── engine/               # Tầng logic nghiệp vụ lõi (Business Rules - Pure Logic)
│   ├── __init__.py
│   └── core.py           # Thuật toán xử lý chính (KHÔNG DÙNG DB)
├── logics/               # Tầng toán học & tiện ích (Pure Functions)
│   └── algorithms.py     # Các hàm tính toán thuần túy
└── tests/                # 🆕 Unit Tests & Integration Tests riêng cho module
    ├── __init__.py
    ├── test_engine.py    # Test logic tính toán (Không cần DB)
    └── test_flows.py     # Test luồng service/api (Cần DB)

```

## 🔍 2. Giải thích Chi tiết Vai trò & Quy tắc

### A. Tầng Lõi (Core Logic - Inner Layers)
Đây là phần quan trọng nhất, chứa "trí tuệ" của ứng dụng. Nó phải độc lập hoàn toàn với Database và Framework.

#### 1. logics/ (Pure Functions)
* **Mục đích:** Chứa các hàm toán học, công thức tính toán, hoặc logic xử lý chuỗi thuần túy.
* **Quy tắc BẤT DI BẤT DỊCH:**
    * ❌ KHÔNG import Database (`db`).
    * ❌ KHÔNG import Models.
    * ❌ KHÔNG import Flask (`request`, `session`).
    * ✅ Chỉ dùng thư viện chuẩn Python (`math`, `datetime`, `re`...).
* **Ví dụ:** Hàm tính khoảng cách ngày FSRS: `calculate_interval(stability, difficulty)`.

#### 2. engine/ (Business Rules Engine)
* **Mục đích:** Chứa các quy trình xử lý nghiệp vụ phức tạp. Ghép nối các hàm trong `logics` để giải quyết bài toán cụ thể.
* **Quy tắc:**
    * ❌ KHÔNG truy cập Database trực tiếp.
    * ✅ Nhận dữ liệu đầu vào là tham số hoặc DTOs (`schemas.py`).
    * ✅ Trả về kết quả là Dictionaries hoặc DTOs.
* **Lợi ích:** Dễ dàng viết Unit Test (trong `tests/test_engine.py`) mà không cần mock Database.

---

### B. Tầng Ứng dụng (Application Layer - Middle Layers)
Cầu nối giữa bên ngoài (API, DB) và logic lõi.

#### 3. services/ (The Orchestrator - Người Nhạc trưởng)
* **Mục đích:** Điều phối hoạt động của module.
* **Quy tắc:** Nơi **DUY NHẤT** được phép thực hiện:
    * **Query DB:** Lấy dữ liệu từ `models.py`.
    * **Transform:** Chuyển đổi Model -> Schema.
    * **Execute:** Gọi `engine` để xử lý.
    * **Persist:** Lưu kết quả vào DB (`db.session.commit()`).
    * **Signal:** Bắn sự kiện (`signals.py`).

#### 4. events.py & tasks.py (Async Operations)
* **events.py:** Lắng nghe tín hiệu từ module khác để xử lý logic phụ (Side Effects).
    * *Ví dụ:* Nghe FSRS bắn tin "Học xong" -> Gọi `ScoreService` cộng điểm.
* **tasks.py:** Chứa các hàm Celery/Background workers cho các việc nặng (gửi mail, export báo cáo).
    * *Quy tắc:* Tasks gọi services, không chứa logic nghiệp vụ phức tạp.

#### 5. interface.py (The Gatekeeper - Người Gác cổng)
* **Mục đích:** API nội bộ cho các module khác gọi đến.
* **Quy tắc:** Module A muốn gọi Module B **BẮT BUỘC** phải thông qua `interface.py` của B.

#### 6. exceptions.py (Domain Exceptions)
* **Mục đích:** Định nghĩa lỗi nghiệp vụ rõ ràng.
    * *Ví dụ:* `class CardNotDueError(Exception): pass`.
* **Lợi ích:** Giúp tầng `api.py` bắt đúng lỗi `try...except CardNotDueError` để trả về HTTP 400 với message chuẩn, thay vì crash 500.

---

### C. Tầng Giao tiếp & Dữ liệu (Outer Layers)

#### 7. routes/ (Presentation)
* **Mục đích:** Nhận HTTP Request từ người dùng.
* **Quy tắc:**
    * Validate input bằng `schemas.py`.
    * Gọi `services`.
    * Xử lý Exception từ `services`.
    * Trả về JSON/HTML.
    * ❌ KHÔNG chứa logic nghiệp vụ.

#### 8. models.py (Persistence)
* **Mục đích:** Định nghĩa các ORM Models (SQLAlchemy).
* **Quy tắc:** Dùng **String Reference** cho Foreign Keys để tránh lỗi **Circular Import**.

---

## 🔄 3. Luồng Dữ liệu Chuẩn (Happy Path)
**Tính năng:** User ôn tập 1 thẻ Flashcard (Module FSRS).

1.  **Route (`routes/api.py`):**
    * Nhận `POST /api/review {card_id: 101, rating: 3}`.
    * Validate input.
    * Gọi `ReviewService.process_review(101, 3)`.
    * Bắt lỗi `CardNotFoundError` (nếu có) trả về 404.
2.  **Service (`services/review_service.py`):**
    * `Flashcard.query.get(101)` -> Lấy Model.
    * Nếu không thấy -> `raise CardNotFoundError`.
    * Chuyển Model -> `CardInputSchema`.
    * Gọi `FSRSEngine.calculate(CardInputSchema, 3)`.
3.  **Engine (`engine/core.py`):**
    * Nhận Schema (Dữ liệu thuần).
    * Tính toán (dùng `logics/`).
    * Trả về Dictionary kết quả mới.
4.  **Service (Tiếp tục):**
    * Cập nhật Model từ kết quả Engine.
    * `db.session.commit()`.
    * Bắn Signal: `card_reviewed.send()`.
5.  **Events (`gamification/events.py`):**
    * Nghe `card_reviewed` -> Gọi `ScoreService` của module Gamification.

---

## 🛡️ 4. Quy tắc "Bất khả xâm phạm" (Golden Rules)

| Quy tắc | Triết lý |
| :--- | :--- |
| **Engine là Thánh địa** | Không biết DB, không biết Flask. Chỉ biết Python thuần. |
| **Service là Quản gia** | Chỉ có Service mới được quyền chạm vào Database. |
| **Interface là Cổng chính** | Giao tiếp liên module phải qua Interface. Không leo rào. |
| **Event để Gỡ rối** | Dùng Signal/Event để các module không cần biết quá sâu về nhau. |

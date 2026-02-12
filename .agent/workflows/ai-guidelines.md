---
description: AI Guidelines - Quy tắc bắt buộc khi AI làm việc với MindStack project
---

# 🤖 MindStack AI Development Guidelines

**Phiên bản:** 2.0 (Refactor Phase)
**Kiến trúc:** Modular Monolith (Flask)

Tài liệu này là **nguồn sự thật duy nhất (Single Source of Truth)** cho các trợ lý AI khi viết code cho dự án MindStack. Bất kỳ đoạn code nào vi phạm các quy tắc dưới đây sẽ bị coi là **Invalid**.

---

## 1. Nguyên tắc Cốt lõi (Core Principles)

1.  **Architecture First:** Tuân thủ kiến trúc **Modular Monolith**. Các module (ví dụ: `auth`, `learning`, `gamification`) phải hoạt động độc lập nhất có thể.
2.  **Zero-Inference:** Không được tự ý đoán tên bảng, tên hàm hay cấu trúc file. Hãy tìm kiếm (`grep`/`find`) trước khi tạo mới.
3.  **Strict Typing:** Mọi function Python mới đều phải có **Type Hinting** đầy đủ (cả tham số và giá trị trả về).
4.  **No Logic in Routes:** File `routes/` chỉ làm nhiệm vụ nhận Request, Validate dữ liệu và gọi Service. Không viết logic nghiệp vụ (if/else phức tạp) trong route.

---

## 2. Cấu trúc Thư mục Chuẩn (Directory Structure)

Mọi module mới hoặc refactor phải tuân thủ cây thư mục này. Không sáng tạo cấu trúc lạ.

```text
mindstack_app/modules/{module_name}/
├── __init__.py           # Đăng ký Blueprint
├── config.py             # Config mặc định
├── interface.py          # [QUAN TRỌNG] Cổng giao tiếp public cho module khác gọi vào
├── models.py             # Database Models (SQLAlchemy)
├── schemas.py            # Pydantic/Marshmallow Schemas (Validation)
├── events.py             # Xử lý sự kiện (Signals receiver)
├── services/             # Logic nghiệp vụ (Business Logic)
│   ├── __init__.py
│   └── {entity}_service.py
├── engines/              # [Dành riêng cho module Learning/Game] Logic tính toán phức tạp
│   ├── base.py           # Abstract Base Classes
│   └── {strategy}.py     # Concrete Implementation
├── routes/               # Presentation Layer
│   ├── api.py            # Trả về JSON (cho Frontend/Mobile)
│   └── views.py          # Trả về HTML (Render Template)
└── tests/                # Unit Tests

## 3. Quy tắc Giao tiếp giữa các Module (Inter-module Communication)

Đây là phần quan trọng nhất để tránh "Spaghetti Code" và giữ cho kiến trúc Modular Monolith được sạch sẽ.

* **CẤM:** `from mindstack_app.modules.OTHER_MODULE.services import Service`
    * *Lý do:* Gây phụ thuộc vòng tròn (Circular Dependency) và phá vỡ tính độc lập của module.
* **ĐƯỢC PHÉP:**
    1.  **Import qua Interface:** Chỉ được import từ file `interface.py` của module khác. File này đóng vai trò là "cổng public" (Public API) của module đó.
    2.  **Sử dụng Signals:** Để module A thông báo sự kiện cho module B mà không cần biết B là ai (ví dụ: `user_registered`, `session_completed`). Module B sẽ lắng nghe sự kiện này trong `events.py`.
    3.  **Foreign Keys dạng chuỗi:** Sử dụng chuỗi string cho relationship trong SQLAlchemy (ví dụ: `relationship('User')` thay vì import class `User`).

---

## 4. Quy tắc Database & Models

1.  **Unified Tables (Bảng thống nhất):**
    * Ưu tiên sử dụng `LearningSession` (bảng `learning_sessions`) cho mọi hoạt động học tập (Quiz, Flashcard, Course).
    * Ưu tiên sử dụng `LearningItem` (bảng `learning_items`) cho nội dung câu hỏi/thẻ bài.
    * Dùng cột `mode` và `type` để phân loại (Discriminator - Đa hình), tránh tạo bảng mới (như `vocab_sessions`, `quiz_sessions`) trừ khi dữ liệu quá đặc thù không thể gộp.
2.  **Mixins:** Luôn sử dụng `TimestampMixin` (cung cấp `created_at`, `updated_at`) cho mọi bảng mới.
3.  **Naming:** Tên bảng (table name) phải ở dạng số nhiều (plural), snake_case (ví dụ: `learning_sessions`, `user_streaks`).

---

## 5. Quy tắc Frontend & Templates (`aura-mobile`)

MindStack sử dụng giao diện Server-side Rendering với theme `aura-mobile`.

* **Vị trí Template:**
    * Bắt buộc đặt tại: `mindstack_app/themes/aura_mobile/templates/aura_mobile/modules/{module_name}/...`
* **Component hóa (Chia nhỏ):**
    * Không viết file HTML dài quá 300 dòng.
    * Tách nhỏ thành các partials bắt đầu bằng dấu gạch dưới `_` (ví dụ: `_card.html`, `_modal_score.html`, `_progress_bar.html`).
    * Sử dụng `{% include %}` để tái sử dụng các thành phần này.
* **Javascript:**
    * Hạn chế viết inline JS `<script>...</script>` trong file HTML, trừ khi cần truyền biến từ Python sang (ví dụ: `const SESSION_ID = {{ session.id }};`).
    * File JS logic phải đặt tại: `mindstack_app/themes/aura_mobile/static/{module_name}/js/`.

---

## 6. Quy trình Refactor (Step-by-Step for AI)

Khi được yêu cầu Refactor hoặc thêm tính năng mới, AI phải tuân thủ trình tự sau để đảm bảo logic không bị gãy:

1.  **Bước 1 - Schema & Model:** Định nghĩa dữ liệu trước (`models.py`). Đảm bảo khớp với các bảng core như `LearningSession` nếu là tính năng học tập.
2.  **Bước 2 - Engine/Strategy:** Viết logic tính toán lõi trong thư mục `engines/` (ví dụ: thuật toán tính điểm, thuật toán chọn thẻ FSRS). Logic này **không được** phụ thuộc vào Flask `request` hay `db` session trực tiếp, nó chỉ xử lý dữ liệu thuần.
3.  **Bước 3 - Service:** Viết Service (`services/`) để kết nối Database với Engine. Service chịu trách nhiệm gọi DB, gọi Engine, và `commit` transaction.
4.  **Bước 4 - Route:** Viết API/View (`routes/`) để gọi Service. Route chỉ làm nhiệm vụ điều hướng, không chứa logic nghiệp vụ.
5.  **Bước 5 - Template:** Tạo giao diện (`templates/`) hoặc cập nhật JSON response.

---


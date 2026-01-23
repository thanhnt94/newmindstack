---
description: AI Guidelines - Quy tắc bắt buộc khi AI làm việc với MindStack project
---

# MindStack Architectural Guidelines

Tài liệu này quy định các tiêu chuẩn thiết kế và phát triển cho dự án MindStack theo kiến trúc Modular Monolith.

## 1. Nguyên lý cốt lõi (Core Principles)
1.  **Strict Separation of Concerns:** Tách biệt tuyệt đối giữa Logic, Database, và Giao diện (Templates).
2.  **Centralized Presentation:** Toàn bộ HTML/Template phải nằm ở thư mục `templates` gốc, không nằm trong module.
3.  **Loose Coupling:** Các module giao tiếp qua Signals/Events, hạn chế gọi trực tiếp.

## 2. Cấu trúc 3 Tầng (The 3-Layer Architecture)

Mọi module phải tuân thủ cấu trúc phân tầng sau:

### Tầng 1: Pure Logic (`/logics`) - "Bộ Não"
* **Trách nhiệm:** Chứa thuật toán, công thức toán học, xử lý dữ liệu thô.
* **Quy tắc CẤM:** KHÔNG import `flask`, `sqlalchemy`, `db`.
* **Ví dụ:** Tính toán ngày rơi FSRS, tính streak.

### Tầng 2: Services (`/services`) - "Quản Lý"
* **Trách nhiệm:** Tương tác Database, gọi Logic, xử lý nghiệp vụ.
* **Quy tắc:** Nơi duy nhất được gọi `db.session.commit()`.

### Tầng 3: Routes/Controllers (`/routes.py`) - "Cổng Giao Tiếp"
* **Trách nhiệm:** Nhận Request, gọi Service, trả về Template/JSON.
* **Quy tắc:** Chỉ làm nhiệm vụ điều hướng, không chứa logic nghiệp vụ.

## 3. Quy tắc về Giao diện (Frontend & Templates)

Hệ thống sử dụng cơ chế **Centralized Templates** để hỗ trợ Theming (Admin/Aura):

* **Vị trí:** Tất cả file `.html` nằm trong `mindstack_app/templates/`.
* **Cấu trúc thư mục Template:**
    * `templates/admin/`: Giao diện quản trị.
    * `templates/aura/pages/<tên_module>/`: Giao diện người dùng theo theme Aura.
* **Quy tắc Module:** Module Code **KHÔNG** được chứa thư mục `templates`. Khi render, Route sẽ trỏ về đường dẫn trong `templates/` gốc.

## 4. Cấu trúc thư mục chuẩn cho một Module (Backend Only)

```text
mindstack_app/modules/tên_module/
├── __init__.py          # Khai báo Blueprint
├── routes.py            # Web Endpoints (Render template từ ../../templates)
├── models.py            # Database Models
├── services/            # Business Services
│   ├── __init__.py
│   └── feature_service.py
├── logics/              # Pure Python Logic
│   ├── __init__.py
│   └── algorithm.py
└── events.py            # (Optional) Signal Listeners
# 🧠 MindStack – Architectural Philosophy & Module Standard (v2.0)

---

## 1. 🎯 Triết lý thiết kế (Architectural Philosophy)

**MindStack** được xây dựng theo mô hình **Modular Monolith**.

### Định nghĩa
- Hệ thống được triển khai như một **Monolith**
- Nhưng được phân rã logic thành các **Mini-Apps (Modules)** tự trị

### Mục tiêu
- Đạt được **tính linh hoạt của Microservices**
- Giữ được **sự đơn giản trong quản lý & triển khai** của Monolith

---

## 2. 🧩 Nguyên tắc cốt lõi (Core Principles)

### 1. Self-Contained (Tự trị)
- Mỗi module tự chứa:
  - Logic nghiệp vụ
  - Data model
  - Cấu hình
  - Giao diện

### 2. Resilient (Kiên cường)
- Cơ chế fallback cấu hình:

    Database (Dynamic)  
      ↓  
    Environment (.env)  
      ↓  
    Module Config (Hardcoded)

### 3. Strict Layering (Phân tầng chặt chẽ)
- Luồng dữ liệu 1 chiều:

    Route (Giao tiếp)  
      ↓  
    Service (Điều phối)  
      ↓  
    Engine (Quy trình)  
      ↓  
    Logic (Toán học / Validate)

### 4. Resilient Dependency (Phụ thuộc an toàn)
- Module giao tiếp thông qua:
  - `interface.py`
  - String Reference trong Database
- Tránh tuyệt đối **Circular Import**

---

## 3. 📁 Cấu trúc thư mục chuẩn (Standard Directory Tree)

    mindstack_app/modules/{module_name}/
    ├── __init__.py           # Đăng ký Blueprint & Metadata
    ├── config.py             # DefaultConfig
    ├── models.py             # SQLAlchemy Models (String Reference)
    ├── schemas.py            # DTOs & Validation
    ├── interface.py          # Public API cho module khác
    ├── routes/
    │   ├── api.py            # Endpoint JSON / AJAX
    │   └── views.py          # Route render HTML
    ├── services/             # Orchestrator
    ├── engine/               # Stateful Workflow
    └── logics/               # Stateless Pure Functions

---

## 4. 🔗 Quy tắc phụ thuộc (Dependency Rules)

| Component | ĐƯỢC PHÉP Import | TUYỆT ĐỐI KHÔNG Import |
|----------|------------------|-----------------------|
| Logics   | Standard Library | DB, Models, Service, Flask |
| Engine   | Logics, Schemas  | DB, Models, Service, Flask Request |
| Service  | DB, Models, Schemas, Engine | Routes, Module khác (trừ interface) |
| Routes   | Service, Schemas | Models trực tiếp, Engine, Logic |

---

## 5. ✅ Refactor Checklist – Official v2.0

### A. Khởi tạo & Metadata (Initialization)

- [ ] `__init__.py` phải chứa `module_metadata` đầy đủ  
      (`name`, `icon`, `url_prefix`, `enabled`, `category`)
- [ ] `setup_module(app)` chỉ đăng ký:
  - Signals
  - Admin routes
  - Context processor  
  ❌ Không chứa logic nghiệp vụ
- [ ] `config.py` phải có `DefaultConfig`
- [ ] Service lấy config theo thứ tự:  
  Database → .env → DefaultConfig

---

### B. Tách biệt Logic & Dữ liệu (Decoupling)

- [ ] Mọi thuật toán / tính toán đặt trong `logics/`
- [ ] Logic thuần **không import** DB, Models, Flask
- [ ] Route → Service → Engine **phải dùng schemas**
- [ ] Không truyền `request.form` trực tiếp
- [ ] Engine không truy cập Session / Request
- [ ] Service chịu trách nhiệm lấy & truyền state

---

### C. Database & Quan hệ (Database Relations)

- [ ] `ForeignKey` và `relationship` dùng **String Reference**
  Ví dụ: db.relationship("User")
- [ ] Không import Model module khác
- [ ] Query chéo bắt buộc thông qua `interface.py`

---

### D. Giao diện & Routing (Presentation)

- [ ] Tách route:
  - `routes/api.py` → JSON / AJAX
  - `routes/views.py` → HTML
- [ ] Template đặt tại:

    themes/{active_theme}/templates/{active_theme}/modules/{module_name}/

- [ ] Render đúng namespace:  
  render_template("modules/learning/index.html")

---

### E. Giao tiếp liên Module (Inter-Module Communication)

- [ ] Public API của module **bắt buộc** qua `interface.py`
- [ ] Dùng Blinker Signals cho event async:
  - user_registered
  - course_completed

---

### F. Kiểm thử & Dọn dẹp (Cleanup)

- [ ] Xóa legacy / dead code
- [ ] Kiểm tra import thừa
- [ ] Không circular import
- [ ] Tuân thủ Dependency Rules

---
### G. Đồng bộ & Loại bỏ Logic trùng lặp (Post-Refactor Cleanup)

- [ ] **Cross-Module Audit**  
  Sau khi refactor xong một logic / service / engine:
  - Tìm kiếm toàn bộ project để kiểm tra:
    - Logic tương tự
    - Hàm trùng chức năng
    - Quy trình xử lý bị lặp
  - Ưu tiên kiểm tra trong:
    - `logics/`
    - `services/`
    - `engine/`

- [ ] **Single Source of Truth**  
  - Mỗi nghiệp vụ **chỉ được tồn tại ở 1 nơi duy nhất**
  - Logic đã refactor xong phải trở thành:
    - Canonical implementation
    - Nguồn dùng chung cho toàn hệ thống

- [ ] **Remove Duplicates**  
  - Xóa toàn bộ:
    - Logic cũ
    - Hàm trùng
    - Code copy-paste
  - ❌ Không giữ lại code “phòng khi cần”

- [ ] **Refactor Consumers**  
  - Các module đang dùng logic cũ phải:
    - Chuyển sang gọi qua `interface.py`
    - Hoặc import từ module chuẩn đã refactor
  - Đảm bảo không phá vỡ Dependency Rules

- [ ] **No Shadow Logic**  
  - Không được tồn tại:
    - Logic bóng (shadow logic)
    - Logic chỉ khác tên nhưng cùng chức năng
  - Nếu cần biến thể → tách thành function rõ ràng

- [ ] **Final Sanity Check**  
  - Chạy lại:
    - Search toàn project
    - Unit / integration test (nếu có)
  - Đảm bảo:
    - Không còn logic trùng
    - Không còn import tới code đã bị xoá

### H. Theme & Frontend Sync (Aura Mobile)

- [ ] **Template Localization**
  - Kiểm tra thư mục `themes/aura_mobile/templates/aura_mobile/modules/{module_name}`.
  - Đảm bảo các file `.html` chỉ chứa logic hiển thị (presentation logic), không chứa logic nghiệp vụ (business logic).

- [ ] **Endpoint Synchronization**
  - Quét toàn bộ file Template (`.html`) và JavaScript (`.js`) trong Theme.
  - Cập nhật tất cả các đường dẫn `url_for` hoặc AJAX fetch:
    - Nếu endpoint đã chuyển sang `routes/api.py`, cập nhật URL (thường là `/api/...`).
    - Nếu tên hàm view function thay đổi, cập nhật `url_for('module.view_name')`.

- [ ] **Data Consistency (View Model)**
  - Nếu `Services` trả về DTO/Schema mới:
    - Cập nhật biến trong Jinja2 template để khớp với key của object mới.
    - Ví dụ: trước đây dùng `user.name`, giờ DTO trả về `user_data.full_name` -> Phải sửa template.

- [ ] **Asset Isolation**
  - CSS/JS đặc thù của module phải nằm trong:
    `themes/aura_mobile/static/{module_name}/` hoặc được quản lý gọn gàng.
  - Tránh viết inline JS quá dài trong file HTML.

> **Nguyên tắc vàng:**  
> _Refactor mà không xoá code cũ = tạo thêm rác kiến trúc._


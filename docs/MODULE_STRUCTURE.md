# MindStack Architectural Philosophy & Module Standard

## 1. Triết lý thiết kế (Architectural Philosophy)
MindStack được xây dựng theo mô hình **Modular Monolith**. 
- **Định nghĩa:** Hệ thống là một khối thống nhất (Monolith) khi triển khai, nhưng được phân rã logic thành các **Mini-Apps (Modules)** tự trị.
- **Mục tiêu:** Đảm bảo tính linh hoạt của Microservices nhưng giữ được sự đơn giản trong quản lý và triển khai của Monolith.

## 2. Nguyên tắc cốt lõi (Core Principles)
1. **Self-Contained (Tự trị):** Mỗi module chứa trọn vẹn logic, data model, cấu hình và tests.
2. **Resilient (Kiên cường):** Cơ chế **Fallback** cấu hình: `Environment > Database > Module Config`.
3. **Strict Layering (Phân tầng chặt chẽ):** `Route -> Service -> Engine -> Logic`.
4. **Events-Driven (Hướng sự kiện):** Sử dụng `events.py` để giao tiếp giữa các module mà không gây phụ thuộc chéo.

## 3. Cấu trúc thư mục chuẩn (Standard Directory Tree)
```
mindstack_app/modules/{module_name}/
├── __init__.py           # Đăng ký Blueprint & Metadata
├── config.py             # Class cấu hình mặc định (Fallback)
├── events.py             # [TÙY CHỌN] Định nghĩa Signals (Bắn sự kiện)
├── models.py             # SQLAlchemy Models (Dùng String Ref)
├── schemas.py            # DTOs (Data Transfer Objects)
├── interface.py          # Public API cho các module khác
│
├── routes/               # [BẮT BUỘC] Tách biệt API và View
│   ├── __init__.py       # Gom và đăng ký các routes con vào Blueprint
│   ├── api.py            # [JSON] Chỉ trả về JSON (phục vụ Mobile/AJAX)
│   └── views.py          # [HTML] Chỉ trả về HTML (Render Template cho Web)
│
├── services/             # Orchestrator (Logic DB & Điều phối)
├── engine/               # Stateful Logic (Xử lý quy trình)
└── logics/               # Stateless Logic (Toán học/Validate)
```

## 4. Quy tắc phụ thuộc (Dependency Rules)
| Component | ĐƯỢC PHÉP Import | TUYỆT ĐỐI KHÔNG Import |
| :--- | :--- | :--- |
| **Logics** | Standard Libs | DB, Models, Service, Flask |
| **Engine** | Logics, Schemas | DB, Models, Service, Flask Request |
| **Service** | DB, Models, Schemas, Engine, Events | Routes |
| **Routes** | Service, Schemas | Models trực tiếp, Engine Logic |

## 5. Refactor Checklist (Dành cho Dev & AI)
- [ ] **Khởi tạo:** Blueprint đã được đăng ký kèm `module_metadata`.
- [ ] **Thành phần lõi (Check-and-Build):**
    - [ ] **`interface.py`**: Module có cung cấp tính năng cho module khác dùng không?
    - [ ] **`events.py`**: Module có cần thông báo cho hệ thống khi có thay đổi không?
    - [ ] **`schemas.py`**: Có dùng DTO thay vì truyền raw Models không?
- [ ] **Giao tiếp (Routes Separation):**
    - [ ] **`routes/api.py`**: Đã tách riêng và **chỉ trả về JSON** chưa?
    - [ ] **`routes/views.py`**: Đã tách riêng và **chỉ trả về HTML** (Template) chưa?
- [ ] **Dọn dẹp:** Đã rà soát **100% số file**. Xóa bỏ hoàn toàn code thừa/comment rác.
- [ ] **Tài liệu:** Đã tạo file `docs/modules/MODULE_{module_name}.md` giải thích **tất cả** các file.
- [ ] **Kiểm thử:** Có ít nhất một file `tests/test_logics.py` chạy độc lập.
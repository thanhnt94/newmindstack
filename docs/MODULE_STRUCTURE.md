# MindStack Architectural Philosophy & Module Standard

## 1. Triết lý thiết kế (Architectural Philosophy)
MindStack được xây dựng theo mô hình **Modular Monolith**. 
- **Định nghĩa:** Hệ thống là một khối thống nhất (Monolith) khi triển khai, nhưng được phân rã logic thành các **Mini-Apps (Modules)** tự trị.
- **Mục tiêu:** Đảm bảo tính linh hoạt của Microservices nhưng giữ được sự đơn giản trong quản lý và triển khai của Monolith.

## 2. Nguyên tắc cốt lõi (Core Principles)
1. **Self-Contained (Tự trị):** Mỗi module chứa trọn vẹn logic, data model, cấu hình và tests. Một module có thể "sống" độc lập về mặt logic.
2. **Resilient (Kiên cường):** Hệ thống không bao giờ "chết" vì thiếu dữ liệu cấu hình. Luôn có cơ chế **Fallback**: `Environment (.env) > Database (Dynamic) > Module Config (Hardcoded)`.
3. **Strict Layering (Phân tầng chặt chẽ):** Tuân thủ luồng dữ liệu 1 chiều: `Route (Giao tiếp) -> Service (Điều phối) -> Engine (Quy trình) -> Logic (Toán học/Validate)`.
4. **Resilient Dependency (Phụ thuộc an toàn):** Các module liên kết với nhau qua `interface.py` hoặc "String Reference" trong database để tránh vòng lặp phụ thuộc (Circular Imports).

## 3. Cấu trúc thư mục chuẩn (Standard Directory Tree)
```
mindstack_app/modules/{module_name}/
├── __init__.py           # Đăng ký Blueprint & Metadata
├── config.py             # Class cấu hình mặc định (Fallback)
├── models.py             # SQLAlchemy Models (Dùng String Ref)
├── schemas.py            # DTOs (Data Transfer Objects)
├── interface.py          # Public API cho các module khác gọi vào
├── routes/               # api.py (JSON) & views.py (HTML)
├── services/             # Orchestrator (Logic DB & Điều phối)
├── engine/               # Stateful Logic (Xử lý quy trình theo DTO)
└── logics/               # Stateless Logic (Hàm thuần túy, không DB/Flask)
```

## 4. Quy tắc phụ thuộc (Dependency Rules)
| Component | ĐƯỢC PHÉP Import | TUYỆT ĐỐI KHÔNG Import |
| :--- | :--- | :--- |
| **Logics** | Standard Libs | DB, Models, Service, Flask |
| **Engine** | Logics, Schemas | DB, Models, Service, Flask Request |
| **Service** | DB, Models, Schemas, Engine | Routes |
| **Routes** | Service, Schemas | Models trực tiếp, Engine Logic |

## 5. Refactor Checklist (Dành cho Dev & AI)
- [ ] **Khởi tạo:** Blueprint đã được đăng ký kèm `module_metadata` trong `__init__.py`.
- [ ] **Cấu hình:** File `config.py` đã có class `DefaultConfig` cho fallback.
- [ ] **Database:** Các Models dùng String Reference (ví dụ: `db.relationship('User')`).
- [ ] **Tách biệt Logic:** Các hàm toán học/xử lý chuỗi đã nằm trong `logics/` và không dính context Flask/DB.
- [ ] **Điều phối:** Tầng `Service` xử lý việc chuyển đổi từ Model sang DTO trước khi đưa vào `Engine`.
- [ ] **Giao tiếp:** `api.py` và `views.py` đã được tách biệt rõ ràng.
- [ ] **Kiểm thử:** Có ít nhất một file `tests/test_logics.py` chạy độc lập với DB.
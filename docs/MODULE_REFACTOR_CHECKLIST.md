# 🚀 MindStack v2.0 - Ultimate Module Refactor Checklist (v3.0 Revised)

Checklist này được xây dựng dựa trên kiến trúc **Modular Monolith (Hexagonal Style)**.  
**Mục tiêu:** Tối ưu hóa quy trình, chỉ tạo những gì thực sự cần thiết ("Pay as you go").

---

## 1. 🛡️ Chuẩn bị & Quản lý rủi ro (Risk Management)
*(Bắt buộc hoàn thành trước khi chạm vào code)*

- [ ] **Branching:** Tạo nhánh git mới cho module (ví dụ: `refactor/module-fsrs`).
- [ ] **Impact Analysis:** Sử dụng search (`Ctrl+Shift+F`) để tìm tất cả các file đang import class/model cũ.
- [ ] **Database Backup:** Dump dữ liệu SQL hoặc copy file `.db` ra thư mục backup an toàn.
- [ ] **Clean State Check:** Chạy `flask db migrate` để đảm bảo schema DB hiện tại đang khớp 100% với code.

---

## 2. 🏗️ Cấu trúc Thư mục (Directory Structure)
**Nguyên tắc:** Chỉ tạo những file thực sự cần thiết cho module cụ thể.

### A. Thành phần Cốt lõi (Bắt buộc 100%)
- [ ] **`__init__.py`**: Khai báo `module_metadata` (tên, icon, key) và hàm `setup_module(app)` để đăng ký Blueprint.
- [ ] **`config.py`**: Chứa class `DefaultConfig` (dù rỗng cũng phải có để tránh lỗi import).
- [ ] **`interface.py` (Gatekeeper)**: Mọi hàm giao tiếp với bên ngoài PHẢI nằm ở đây.

### B. Thành phần Dữ liệu & Logic (Tùy chọn)
- [ ] **`models.py`**: Chỉ cần khi module có bảng Database riêng. (Lưu ý: Dùng String Reference cho quan hệ).
- [ ] **`schemas.py`**: Cần khi có API input/output phức tạp hoặc cần truyền data vào Engine.
- [ ] **`services/`**: Cần khi có logic CRUD hoặc tương tác Database.
- [ ] **`engine/` & `logics/`**: Cần khi module có thuật toán phức tạp (FSRS, Scoring). *Không cần khi chỉ là CRUD đơn giản.*

### C. Thành phần Mở rộng (Nâng cao)
- [ ] **`routes/`**: Gồm `api.py` (JSON) hoặc `views.py` (HTML).
- [ ] **`events.py` (Listeners)**: Cần khi muốn nghe sự kiện từ module khác.
- [ ] **`signals.py` (Emitters)**: Cần khi muốn thông báo sự kiện cho hệ thống.
- [ ] **`tasks.py`**: Cần cho tác vụ chạy ngầm hoặc định kỳ (Celery).
- [ ] **`exceptions.py`**: Định nghĩa lỗi nghiệp vụ đặc thù (VD: `CardNotDueError`).

---

## 3. 💾 Database & Migrations
- [ ] **Relocation:** Chuyển model từ thư mục cũ về `modules/{name}/models.py`.
- [ ] **Logic Cleanup:** Xóa các hàm logic trong Model (VD: `save()`, `calculate()`). Model chỉ chứa định nghĩa cột.
- [ ] **Migration:**
    * Chạy: `flask db migrate -m "refactor: {module}"`
    * **REVIEW:** Kiểm tra file migration, tuyệt đối không được có `DROP TABLE` (trừ khi chủ đích).

---

## 4. 🧠 Logic Lõi & Engine (Nếu có)
*(Quy tắc vàng: Engine không biết Database là gì)*

- [ ] **Pure Logics:** File trong `logics/` chỉ import thư viện chuẩn Python (`math`, `datetime`...).
- [ ] **Engine Isolation:** File `engine/core.py` **KHÔNG** import models hay db. Chỉ nhận DTO/Tham số.

---

## 5. 🛠️ Dịch vụ & Điều phối (Service Layer)
- [ ] **Access Control:** Chỉ Service mới được gọi `Model.query` và `db.session`.
- [ ] **Transformation:** Chuyển đổi Model <-> Schema trước khi gọi Engine.
- [ ] **Workflow:** Thực hiện đúng trình tự: `Query DB` -> `Convert Schema` -> `Call Engine` -> `Save DB` -> `Emit Signal`.

---

## 6. 🔌 Giao tiếp & Sự kiện
- [ ] **Gatekeeper:** Module khác chỉ được import thông qua `interface.py`.
- [ ] **Decoupling:** Thay vì gọi trực tiếp Service của module khác, hãy bắn Signal (`signals.py`) và để module kia tự lắng nghe (`events.py`).

---

### 7. 🌐 Giao diện & API
- [ ] **Validation:** Đảm bảo mọi API Endpoint sử dụng `schemas.py` để validate request body trước khi xử lý.
- [ ] **Template Sync (QUAN TRỌNG):**
    - [ ] Kiểm tra toàn bộ các file `.html` liên quan trong thư mục `themes/`.
    - [ ] Đảm bảo các biến Jinja2 (ví dụ: `{{ user.full_name }}`) khớp hoàn toàn với Model hoặc Schema mới.
    - [ ] Nếu đổi tên hàm View, phải cập nhật lại toàn bộ các lời gọi `url_for('module.view_func')`.
- [ ] **Paths:**
    * **Template:** `themes/{theme}/templates/{theme}/modules/{module_name}/`
    * **Static:** `static/{module_name}/`

---

## 8. 🧪 Kiểm thử & Tài liệu
- [ ] **Unit Test:** Nếu có engine, bắt buộc phải có test case trong `tests/`.
- [ ] **Smoke Test:** Chạy thử luồng chính (Happy Path) trên trình duyệt.
- [ ] **README.md:** Ghi rõ module làm gì, phụ thuộc ai, và danh sách sự kiện (Listen/Emit).

---

## 🧹 Final Polish
- [ ] **Dead Code:** Xóa file cũ/code cũ sau khi migrate thành công.
- [ ] **Linter:** Kiểm tra code sạch, tuân thủ chuẩn PEP8.
- [ ] **Active Check:** Đảm bảo module hiển thị đúng trong Admin Panel.

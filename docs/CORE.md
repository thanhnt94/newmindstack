# 🏗️ MindStack Core Documentation

## Overview
Thư mục `mindstack_app/core/` là "trái tim" của hệ thống, chịu trách nhiệm điều phối (Orchestration), cấu hình và cung cấp hạ tầng cho toàn bộ ứng dụng. Code trong Core phải mang tính tổng quát, không chứa logic nghiệp vụ của bất kỳ module cụ thể nào.

---

## 📂 Thành phần chính

### 1. `bootstrap.py` (The System Heart)
Chịu trách nhiệm khởi động ứng dụng. Hàm `bootstrap_system(app)` thực hiện các bước:
- Khởi tạo Extensions (DB, Migrate, CSRF).
- Đăng ký Global Error Handlers và Jinja2 Filters.
- **Auto-Discovery Modules**: Tự động quét thư mục `modules/` và nạp Blueprints.
- **Theme Activation**: Nạp giao diện người dùng dựa trên cấu hình.

### 2. `config.py`
Quản lý cấu hình hệ thống từ:
- Biến môi trường (`.env`).
- Cấu hình mặc định trong code.
- **Dynamic Config**: Tích hợp với `ConfigService` để nạp các cài đặt từ Database vào `app.config`.

### 3. `extensions.py`
Nơi khởi tạo duy nhất cho các Flask Extensions.
- **Quy tắc**: Không khởi tạo extension trực tiếp trong module. Luôn import từ core để tránh vòng lặp (circular imports).

### 4. `module_registry.py`
Theo dõi danh sách các module đã được nạp thành công. Cung cấp API để các module khác có thể kiểm tra sự tồn tại của nhau.

---

## 🛠️ Hướng dẫn viết code trong Core

### Khi nào thêm code vào Core?
- Khi bạn cần thêm một Flask Extension mới (ví dụ: SocketIO, Mail).
- Khi bạn cần tạo một Jinja2 Filter dùng chung cho toàn bộ hệ thống.
- Khi bạn cần thay đổi cơ chế khởi động ứng dụng.

### Quy tắc "Vàng":
1. **Không chứa Business Logic**: Core không được biết về "Flashcard", "Quiz" hay "User Points".
2. **Safe Loading**: Code trong core phải bao bọc trong `try-except` khi thực hiện các thao tác load động để tránh làm sập toàn bộ app nếu một module bị lỗi.
3. **Thứ tự import**: Tránh import từ `mindstack_app.modules` vào Core. Core chỉ nên cung cấp hạ tầng cho Modules sử dụng.

---

## 🔄 Luồng khởi tạo (Bootstrap Flow)
1. `create_app()` (factory) gọi `bootstrap_system(app)`.
2. `init_infrastructure`: Gắn SQLAlchemy, CSRF,...
3. `load_modules`: Duyệt từng thư mục con trong `modules/`.
4. `setup_module`: Gọi hàm setup của từng module (nếu có).
5. `load_themes`: Đăng ký Blueprint của Theme đang hoạt động.

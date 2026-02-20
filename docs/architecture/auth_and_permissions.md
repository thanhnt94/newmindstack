# Kiến Trúc Xác Thực & Phân Quyền (Auth & Permissions)

MindStack quản lý người dùng (Users), phiên đăng nhập (Sessions) và quyền truy cập (Access Control) thông qua một số module chuyên biệt.

---

## 1. Module Auth (`mindstack_app/modules/auth`)

Module `auth` chịu trách nhiệm cốt lõi cho vòng đời định danh (Identity Lifecycle) của người dùng:
- **Đăng ký (Registration)**: Băm mật khẩu (Password Hashing) bằng `Werkzeug.security`.
- **Đăng nhập (Login)**: Xác thực Creditentials. 
- **Quản lý Phiên (Session Management)**: MindStack hiện đang sử dụng cơ chế **Cookie-based Session** mặc định của Flask (`flask_login` / `session`). 
  - Token định danh được mã hóa an toàn và gửi về trình duyệt dưới dạng `HttpOnly` Cookie.
  - Phù hợp cho kiến trúc Web App hiện tại (Server-Side Rendering + chút xíu Client-Side JS). 
  - Tương lai (nếu làm Mobile Native App) có thể mở rộng thêm JWT API.
- **Model chính**: Bảng `users` với các cột `username`, `email`, `password_hash`, `user_role`.

---

## 2. Module Access Control (`mindstack_app/modules/access_control`)

Được tách biệt hoàn toàn khỏi Logic Authentication, module `access_control` chịu trách nhiệm trả lời câu hỏi: *"User X (Role Y) có được phép thực hiện hành động Z lên Tài nguyên W hay không?"*.

Việc này giúp tránh tình trạng rải rác lệnh `if user.role == 'admin':` khắp codebase.

### Thẩm Định Quyền (Authorizers)
Các dịch vụ nghiệp vụ (Business Services) gọi qua `AccessControlInterface.enforce_permission(...)` để thẩm định quyền:
1. Quyền dựa theo **Chức vụ (Role-Based Access Control - RBAC)**:
   - Admin được truy cập `mindstack_app/modules/admin/` và `/manage/content/`.
   - Normal User chỉ được truy cập các Route học tập (`/learning`, `/dashboard`).
2. Quyền dựa theo **Định kiến (Resource-Based or Attribute-Based Access Control - ABAC)**:
   - Một Normal User (Role = User) chỉ được sửa chữa Khóa Học A, nếu `CourseA.creator_user_id == user.user_id`. (Tức là chỉ tác giả mới có quyền sửa).

---

## 3. Decorators (Cổng Bảo Vệ Routes)

Tại tầng Routing / Controllers, MindStack áp dụng các Decorator (định nghĩa trong `utils/decorators.py` hoặc ngay trong các module):
- `@login_required`: Đảm bảo Request bắt buộc phải có Cookie hợp lệ (Đã đăng nhập) mới được tiến vào hàm xử lý Logic. Nếu không, redirect ra `/auth/login`.
- `@admin_required`: Đảm bảo Cookie thuộc về user có `role='admin'`. Thường áp đặt ở cấp độ Blueprint (cho toàn bộ Route trong file đó).

---

## 4. Tương Tác Giữa Các Hệ Thống

`auth` hoạt động như một nhà cung cấp định danh trung tâm (Identity Provider):
- Bất kỳ khi nào một Request cần lấy thông tin (`current_user`), nó có thể import qua cơ chế của Flask, hoặc lấy trực tiếp từ `AuthInterface.get_user_by_id(user_id)`.
- FSRS, History, Gamification đều liên kết dữ liệu theo `user_id` có nguồn gốc từ bảng `users`.
- Để tránh vòng lặp Import (Circular Dependencies), mọi module khác cấm import trực tiếp Model `User` từ thư mục `auth/models.py`. Phải gọi thông qua `AuthInterface` và lấy về đối tượng DTO (Data Transfer Object) như `UserDTO`.

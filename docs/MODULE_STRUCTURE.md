📁 Cấu trúc thư mục chuẩn (Standard Directory Tree)
Plaintext
mindstack_app/modules/{module_name}/
├── __init__.py           # Đăng ký và quản lý Metadata
├── config.py             # Cấu hình mặc định (Default Config)
├── models.py             # Định nghĩa cấu trúc dữ liệu (SQLAlchemy)
├── schemas.py            # Chuyển đổi và xác thực dữ liệu (DTOs)
├── interface.py          # Cổng giao tiếp duy nhất cho module khác
├── routes/               # Tầng giao tiếp (Presentation Layer)
│   ├── api.py            # Endpoints cho JSON / AJAX / Mobile app
│   └── views.py          # Endpoints render HTML (Jinja2)
├── services/             # Tầng điều phối (Orchestrator Layer)
├── engine/               # Tầng xử lý quy trình (Stateful Workflow)
└── logics/               # Tầng thuật toán thuần (Stateless Pure Functions)


📄 Chi tiết mục đích của từng file
1. __init__.py (Initialization & Metadata)
Mục đích: Khai báo module như một package Python.
Nội dung: Chứa module_metadata (tên, icon, prefix URL) và hàm setup_module(app) để đăng ký Blueprint, Signals hoặc Context Processors.
2. config.py (DefaultConfig)
Mục đích: Định nghĩa các hằng số và cấu hình mặc định cho module.
Cơ chế: Phải hỗ trợ fallback theo thứ tự: Database → Environment (.env) → DefaultConfig (Hardcoded).
3. models.py (Database Models)
Mục đích: Định nghĩa các bảng Database bằng SQLAlchemy.
Quy tắc: Sử dụng String Reference (ví dụ: db.relationship("User")) cho các mối quan hệ để tránh lỗi Circular Import. Không import trực tiếp Model từ module khác.
4. schemas.py (DTOs & Validation)
Mục đích: Định nghĩa cấu trúc dữ liệu đầu ra/đầu vào (thường dùng Pydantic hoặc Marshmallow).
Vai trò: Đóng vai trò là "vật mang tin" giữa các tầng (Route ↔ Service ↔ Engine), giúp dữ liệu luôn sạch và đúng định dạng.
5. interface.py (Public API)
Mục đích: Là "cánh cửa" duy nhất để các module khác tương tác với module này.
Quy tắc: Mọi truy vấn hoặc gọi hàm chéo giữa các module bắt buộc phải đi qua file này.
6. routes/ (Presentation Layer)
api.py: Chứa các logic xử lý endpoint trả về JSON cho phía Frontend hoặc Mobile App.
views.py: Xử lý render các trang HTML. Lưu ý: Template phải đặt trong thư mục theme tương ứng (ví dụ: aura_mobile).
7. services/ (Orchestrator Layer)
Mục đích: Là tầng trung gian điều phối dữ liệu từ Database, gọi các Engine và Logics để trả về kết quả cho Routes.
Quy tắc: Chịu trách nhiệm quản lý state và lấy cấu hình từ Config Service.
8. engine/ (Stateful Workflow)
Mục đích: Chứa các quy trình xử lý có trạng thái (ví dụ: quy trình tính toán SRS, quy trình làm Quiz).
Quy tắc: Không truy cập trực tiếp vào Session hay Flask Request.
9. logics/ (Stateless Pure Functions)
Mục đích: Chứa các hàm toán học, thuật toán thuần túy hoặc logic validate không phụ thuộc vào trạng thái hệ thống.
Quy tắc: Tuyệt đối không import Database, Models hay Flask. Điều này giúp logic dễ dàng được tái sử dụng và kiểm thử (Unit Test).

🛠 Nguyên tắc phụ thuộc (Dependency Rules)
Để giữ hệ thống bền vững (Resilient), bạn cần tuân thủ bảng sau khi viết code:
Logics: Chỉ dùng thư viện chuẩn (Standard Library).
Engine: Được phép dùng Logics và Schemas.
Service: Được phép dùng DB, Models, Schemas và Engine.
Routes: Chỉ được gọi Service và Schemas.

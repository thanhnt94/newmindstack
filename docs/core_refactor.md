HƯỚNG DẪN KIẾN TRÚC CORE SYSTEM (CẤU TRÚC BÊN NGOÀI)1. TỔNG QUAN & TRIẾT LÝTrong kiến trúc Modular Monolith của MindStack, Core System đóng vai trò là cơ sở hạ tầng (Infrastructure).Nhiệm vụ của Core: Cung cấp điện, nước, móng nhà (Database, Config, Logging, Security) cho các Module hoạt động.Nguyên tắc "Agnostic" (Không thiên vị): Core không được biết chi tiết về logic của Flashcard hay Quiz. Core chỉ biết khái niệm chung là "Module".Cơ chế "Plug & Play": Core có khả năng tự động quét và nạp các Module/Themes mà không cần hardcode từng dòng import.2. CẤU TRÚC THƯ MỤC TỔNG QUAN (GLOBAL STRUCTURE)Chúng ta áp dụng cấu trúc "Siêu sạch" (Ultra-Clean): Thư mục gốc chỉ chứa file khởi tạo, toàn bộ hạ tầng kỹ thuật được gói gọn vào core/. Loại bỏ hoàn toàn thư mục templates/ và static/ ở gốc để chuyển về themes/.mindstack_app/
├── __init__.py           # Application Factory (File duy nhất ở root)
│
├── core/                 # [INFRASTRUCTURE LAYER] - Trái tim hệ thống
│   ├── __init__.py
│   ├── config.py         # ✅ [Moved] Cấu hình môi trường (Dev/Prod)
│   ├── extensions.py     # ✅ [Moved] Khởi tạo DB, Migrate, LoginManager...
│   ├── bootstrap.py      # ✅ [Logic Chính] Nạp Modules & Themes
│   ├── error_handlers.py # Xử lý lỗi toàn cục (404, 500)
│   ├── logging_config.py # Cấu hình log chuẩn
│   └── signals.py        # Event Bus trung tâm
│
├── modules/              # [DOMAIN LAYER] - Backend Logic Only
│   ├── AI/
│   ├── Flashcard/
│   ├── Vocabulary/
│   └── ...
│
└── themes/               # [PRESENTATION LAYER] - Frontend Logic (UI/UX)
    │
    ├── admin/            # ✅ [SYSTEM THEME] Giao diện Admin (Luôn được nạp)
    │   ├── __init__.py   # Blueprint('admin_theme')
    │   ├── static/       # CSS/JS Admin
    │   └── templates/    # HTML Admin
    │       ├── admin_base.html  # Layout gốc cho Admin Panel
    │       └── ...
    │
    └── aura_mobile/      # ✅ [USER THEME] Giao diện người dùng (Nạp theo Config)
        ├── __init__.py   # Blueprint('aura_mobile')
        ├── static/       # Assets (CSS/JS/Images)
        └── templates/    # HTML
            ├── base.html # Layout gốc cho User
            └── ...
3. CƠ CHẾ BOOTSTRAP (KHỞI ĐỘNG HỆ THỐNG)Trái tim của hệ thống nằm ở file mindstack_app/core/bootstrap.py.3.1. Auto-Discovery (Tự động phát hiện Module)Thay vì viết import thủ công, hệ thống sẽ quét thư mục modules/.Quy trình:Đọc danh sách ưu tiên từ Config (MODULE_LOAD_PRIORITY).Duyệt qua thư mục mindstack_app/modules/.Tìm file __init__.py.Nếu có blueprint, đăng ký nó (app.register_blueprint).Nếu có module_metadata, thêm vào menu Admin (app.extensions['admin_menu']).3.2. Model Registry (Đăng ký Models)Để giải quyết vấn đề "String Reference" trong SQLAlchemy (tránh Circular Import).Quy trình:Quét file models.py trong tất cả các module con.Import chúng ngay khi App khởi tạo (trong app_context).Kết quả: SQLAlchemy biết User là ai, Flashcard là ai mà không cần import trực tiếp class.3.3. Theme Loading (Nạp Giao diện)Hệ thống sẽ nạp 2 loại theme:Admin Theme (Bắt buộc):Luôn nạp Blueprint từ themes/admin/.Cung cấp admin_base.html để các module kế thừa ({% extends "admin_base.html" %}).Active Theme (Động):Đọc app.config['ACTIVE_THEME'] (ví dụ: "aura_mobile").Nạp Blueprint tương ứng.Cung cấp base.html cho các trang public.Inject helper theme_static vào Jinja2 context.4. QUY TRÌNH TẠO & ĐĂNG KÝ MODULE MỚIBạn không cần sửa file __init__.py của App mỗi khi thêm tính năng. Chỉ cần làm theo các bước sau:Bước 1: Tạo thư mụcTạo mindstack_app/modules/payment/.Bước 2: Tạo __init__.py (Bắt buộc)Đây là "Giấy khai sinh" của module.from flask import Blueprint
from .routes import register_routes # Nếu dùng cấu trúc folder routes/

# 1. Tạo Blueprint (Lưu ý: Không set template_folder ở đây, Theme lo việc đó)
blueprint = Blueprint('payment_module', __name__)

# 2. Đăng ký Routes (Views & API)
register_routes(blueprint)

# 3. Khai báo Metadata (Để hiện trong Admin Panel)
module_metadata = {
    'name': 'Thanh toán',      # Tên hiển thị
    'icon': 'credit-card',     # Icon
    'category': 'Business',    # Nhóm menu
    'admin_route': 'payment_module.admin_dashboard', # Link khi click menu
    'enabled': True            # Trạng thái
}
Bước 3: Restart ServerCore System sẽ tự động tìm thấy folder payment và kích hoạt nó.5. CÁCH TƯƠNG TÁC GIỮA CÁC THÀNH PHẦN5.1. Module gọi CoreModule được phép import các tiện ích từ Core.Lấy Database: from mindstack_app.core.extensions import dbLấy Config: from flask import current_app -> current_app.config['KEY']5.2. Core gọi ModuleCore KHÔNG ĐƯỢC import trực tiếp code của Module (để tránh phụ thuộc ngược).Core chỉ tương tác với Module thông qua:Blueprint: Để điều hướng URL.Signals: Để bắn sự kiện chung.5.3. Module gọi Module (Quan trọng)Tuyệt đối tránh: from modules.flashcard.services import ... (Circular Import).Nên dùng:Interface: from mindstack_app.modules.flashcard.interface import get_card_stats.Events: Lắng nghe sự kiện flashcard_completed từ mindstack_app.modules.flashcard.events.6. QUY TẮC DB MIGRATION (ALEMBIC)Khi bạn thêm models.py vào một module mới:Đảm bảo module đó đã được Core load (Server chạy không lỗi).Chạy lệnh tạo migration:flask db migrate -m "Add payment tables"
Lưu ý: Alembic sẽ tự tìm thấy model mới nhờ cơ chế Model Registry của Core.Chạy lệnh upgrade:flask db upgrade
7. TỔNG KẾT: SƠ ĐỒ PHỤ THUỘC[User Theme] --(kế thừa)--> [Base Layout]
      ^
      |
[Modules UI] --(render)--> [Admin Theme]
      ^
      |
[Modules Logic] --(dùng)--> [Core Infrastructure]
Core: Móng nhà (Hạ tầng).Admin Theme: Khung nhà quản trị (System UI).User Theme: Mặt tiền trang trí (End-user UI).Modules: Các phòng chức năng bên trong (Business Logic).
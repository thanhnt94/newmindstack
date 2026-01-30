HƯỚNG DẪN CẤU TRÚC MODULE & QUẢN LÝ CẤU HÌNH1. TRIẾT LÝ THIẾT KẾ MODULEMỗi module trong MindStack (ví dụ: AI, Flashcard, Gamification) được thiết kế như một ứng dụng thu nhỏ (Mini-App).Nguyên tắc cốt lõi:Self-Contained (Tự trị): Module chứa trọn vẹn logic, data model, cấu hình, và tests của nó.Resilient (Kiên cường): Nếu Database (DB) gặp sự cố, Module tự động chuyển sang sử dụng cấu hình cứng (hardcoded defaults).Strict Layering (Phân tầng chặt chẽ): Tuân thủ luồng dữ liệu 1 chiều: Route -> Service -> Engine -> Logic.2. CẤU TRÚC THƯ MỤC CHUẨN (STANDARD DIRECTORY TREE)Mỗi module tập trung hoàn toàn vào xử lý nghiệp vụ (Backend). Giao diện (UI) được ủy quyền cho hệ thống Theme.Plaintextmindstack_app/modules/{module_name}/
├── __init__.py           # [BẮT BUỘC] Đăng ký Blueprint & Metadata
├── config.py             # [TÙY CHỌN] Class cấu hình mặc định (Fallback)
├── models.py             # [TÙY CHỌN] SQLAlchemy Models (Nếu module có lưu DB)
├── schemas.py            # [KHUYÊN DÙNG] DTOs (Data Transfer Objects)
├── events.py             # [TÙY CHỌN] Định nghĩa Signals (Nếu có bắn sự kiện)
├── interface.py          # [TÙY CHỌN] Public API (Nếu module khác cần gọi vào)
│
├── routes/               # [BẮT BUỘC] Tách biệt API và View
│   ├── __init__.py       # Gom và đăng ký các routes con vào Blueprint
│   ├── api.py            # Trả về JSON (Mobile/AJAX)
│   └── views.py          # Trả về HTML (Render Template)
│
├── services/             # [BẮT BUỘC] Orchestrator (Logic DB & Flow)
│   ├── __init__.py
│   └── main_service.py
│
├── engine/               # [TÙY CHỌN] Stateful Logic (In-Memory)
│   ├── __init__.py
│   └── processor.py      # Xử lý quy trình (Input/Output là DTO)
│
├── logics/               # [TÙY CHỌN] Stateless Logic (Toán học/Validate)
│   ├── __init__.py
│   └── math_utils.py
│
└── tests/                # [KHUYÊN DÙNG] Unit Tests riêng của Module
    ├── __init__.py
    ├── test_logics.py    # Test hàm thuần túy (Không DB)
    └── test_engine.py    # Test quy trình xử lý (Mock DB)
3. CHIẾN LƯỢC QUẢN LÝ CẤU HÌNH (HYBRID CONFIGURATION)Ưu tiên 3 lớp: Environment (.env) > Database (Dynamic) > Module Config (Hardcoded).3.1. File config.pyChứa giá trị mặc định an toàn.Python# modules/AI/config.py
class AIModuleDefaultConfig:
    PROVIDER_TIMEOUT = 30
    DEFAULT_MODEL = "gemini-1.5-flash"
    DEFAULT_TEMPERATURE = 0.7
3.2. Cơ chế Fallback trong ServiceService chịu trách nhiệm gọi AppSetting model, bọc trong try-except. Nếu lỗi DB hoặc không tìm thấy key, fallback về AIModuleDefaultConfig.4. LUỒNG DỮ LIỆU (DATA FLOW)Route (API/View): Nhận request, validate sơ bộ -> Gọi Service.Service:Lấy Config (DB/Fallback).Lấy Data từ DB (Models) -> Convert sang DTO.Khởi tạo Engine (Inject Config & Data).Engine: Xử lý logic nghiệp vụ trên DTO -> Trả về kết quả DTO.Service: Lưu kết quả vào DB -> Bắn Event -> Trả DTO cho Route.5. QUY TẮC PHỤ THUỘC (DEPENDENCY RULES)ComponentĐược phép ImportTUYỆT ĐỐI KHÔNG ImportLogicsStandard LibsDB, Models, Service, Engine, FlaskEngineLogics, SchemasDB, Models, Service, Flask RequestSchemasStandard LibsDB, Models, LogicServiceDB, Models, Schemas, Engine, EventsRoutesRoutesService, SchemasModels, Engine, Logics, DB QueriesModelsDB InstanceModels của module khác (dùng String Ref)6. CHECKLIST KHI TẠO MODULE MỚI[ ] Tạo file config.py với class DefaultConfig.[ ] Tạo folder routes/ và file __init__.py để gom endpoints.[ ] Viết hàm get_config() trong Service có try-except.[ ] Tạo tests/test_logics.py để đảm bảo logic tính toán đúng trước khi viết DB code.7. TÍCH HỢP GIAO DIỆN & ROUTES7.1. Đăng ký Routes con (routes/__init__.py)File này chịu trách nhiệm import api và views để Blueprint nhận diện.Python# modules/{module}/routes/__init__.py
from . import api, views

def register_routes(blueprint):
    # Hàm này giữ chỗ để gọi từ __init__.py chính
    # Trong thực tế, có thể import trực tiếp trong __init__.py
    # Nhưng tách ra giúp __init__.py gọn gàng hơn
    pass
7.2. Xử lý Template AdminModule định nghĩa tên file (Logical Path), nhưng file thực tế nằm ở Theme.Service/View: render_template('ai/admin/settings.html')Vị trí file thật: mindstack_app/themes/admin/templates/ai/admin/settings.html (hoặc theme đang active).8. CHIẾN LƯỢC KIỂM THỬ (TESTING STRATEGY)8.1. Unit Test cho Logics (Nhanh nhất)Chạy trong vài mili-giây. Không cần app_context hay db.Python# modules/flashcard/tests/test_logics.py
from ..logics.fsrs import calculate_next_interval

def test_interval_calculation():
    assert calculate_next_interval(stability=5, rating=3) == 12
8.2. Unit Test cho Engine (Cô lập)Sử dụng dữ liệu giả (Mock DTO) để test quy trình.9. QUY TẮC CẤU TRÚC: FILE ĐƠN HAY THƯ MỤC? (SCALING RULES)Để tránh làm phức tạp hóa vấn đề (Over-engineering), áp dụng quy tắc sau:9.1. Khi nào dùng 1 File .py?routes.py: Khi module < 10 endpoints và chỉ có 1 loại (API hoặc View).services.py: Khi logic đơn giản (CRUD), file < 300 dòng.9.2. Khi nào tách thành Thư mục?routes/: Khi có cả API và Views, hoặc > 15 endpoints.services/: Khi module quản lý nhiều thực thể (FlashcardService, ReviewService).engine/ & logics/: Luôn khuyến khích tách file theo chức năng.10. HƯỚNG DẪN THIẾT KẾ MODELS (MODEL DESIGN GUIDELINES)Để đảm bảo tính độc lập và tránh lỗi Circular Import (vòng lặp phụ thuộc).10.1. Nguyên tắc "String Reference" (Tham chiếu chuỗi)Khi Model A quan hệ với Model B (ở module khác), TUYỆT ĐỐI KHÔNG import class trực tiếp. Hãy dùng chuỗi string.Ví dụ Sai:Pythonfrom mindstack_app.modules.auth.models import User # ❌ CẤM
class Flashcard(db.Model):
    owner = db.relationship(User)
Ví dụ Đúng (Chuẩn Modular):Pythonfrom mindstack_app.core.extensions import db

class Flashcard(db.Model):
    # 1. Foreign Key: Dùng tên bảng ('users.id')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 2. Relationship: Dùng tên Class ('User')
    # SQLAlchemy tự tìm trong registry lúc runtime
    owner = db.relationship('User', backref='flashcards')
10.2. Quy định đặt tên bảngNên (nhưng không bắt buộc) prefix tên bảng bằng tên module để tránh xung đột: flashcards, quiz_questions, gamification_badges.
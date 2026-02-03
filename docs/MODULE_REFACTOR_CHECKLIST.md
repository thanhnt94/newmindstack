🚀 MindStack v2.0 Ultimate Refactor Checklist (Final)
1. 🛡️ Chuẩn bị & Quản lý rủi ro (Risk Control)
Làm trước khi sửa code:
[ ] Check-out Branch: Luôn làm việc trên nhánh mới (ví dụ: refactor/module-name).
[ ] Pre-refactor Search: Tìm kiếm toàn project (Ctrl+Shift+F) tên class/model sắp di chuyển để biết những file nào sẽ bị ảnh hưởng.
[ ] Database Snapshot: Backup dữ liệu .db hoặc dump SQL hiện tại để phòng trường hợp migration làm mất dữ liệu.

2. 🎯 Single Source of Truth (SSoT) Check - QUAN TRỌNG NHẤT
Trước khi viết code logic, hãy tự hỏi:
[ ] Data Ownership: Module này có phải là "chủ sở hữu" duy nhất của dữ liệu này không?
Ví dụ sai: Lưu user_email vào bảng LearningSession (Dữ liệu thừa).
Ví dụ đúng: Chỉ lưu user_id, khi cần email thì gọi qua Interface của module auth.
[ ] Logic Centralization: Logic này đã tồn tại ở module khác chưa?
Ví dụ: Nếu module này cần tính toán ngày ôn tập (SRS), TUYỆT ĐỐI KHÔNG viết lại thuật toán. Phải gọi sang modules.fsrs.interface.
[ ] No "Utility" Abuse: Kiểm tra các file utils/. Nếu logic đó mang tính nghiệp vụ (như calculate_score), hãy đưa nó vào logics/ của module tương ứng, không để ở utils chung.

3. 🏗️ Cấu trúc & Khởi tạo (Structure)
[ ] Standard Tree: Đảm bảo đủ các thư mục/file:
Plaintext
modules/{name}/
├── routes/ (api.py, views.py)
├── services/
├── engine/ (Stateful workflow)
├── logics/ (Stateless algorithms)
├── models.py
├── schemas.py
├── interface.py
├── config.py
└── README.md (Bắt buộc)


[ ] Metadata: __init__.py khai báo đủ module_metadata (name, key, icon...).
[ ] Registry: Hàm setup_module(app) chỉ đăng ký Blueprint/Signals, không chứa logic code.

4. 💾 Database & Migrations (Quy trình chuẩn)
[ ] Model Relocation: Chuyển model từ mindstack_app/models/ vào modules/{name}/models.py.
[ ] String References: Dùng chuỗi cho Foreign Key (VD: db.relationship("User")) để chặn đứng Circular Import.
[ ] Generate Migration:
Chạy: flask db migrate -m "refactor: move {module} models"
REVIEW FILE (BẮT BUỘC): Mở file trong migrations/versions/.
❌ Thấy DROP TABLE: DỪNG LẠI. Alembic đang hiểu nhầm. Phải sửa thành rename_table hoặc alter_table.
✅ Thấy ALTER TABLE / ADD COLUMN: Ổn.
[ ] Apply Migration: Chạy flask db upgrade để đồng bộ DB local.

5. 🛡️ Logic & Phân tầng (Layering)
[ ] Absolute Imports: Sửa toàn bộ import thành dạng tuyệt đối:
✅ from mindstack_app.modules.{name}.interface import ...
[ ] Stateless Logics: Các hàm trong logics/ không được import db, models hay flask.request. Chỉ nhận input -> trả output.
[ ] Orchestrator: services/ làm nhiệm vụ lấy config, gọi engine, gọi models, và trả về schemas.
[ ] Type Hints: Sử dụng Type Hint đầy đủ trong interface.py để IDE hỗ trợ nhắc lệnh cho module khác.

6. 🔌 Giao tiếp (Interface Gateway)
[ ] Gatekeeper Rule: Mọi hàm mà module khác cần dùng bắt buộc phải khai báo trong interface.py.
[ ] Event Driven: Nếu logic không cần trả kết quả ngay (VD: gửi email, tính stats), hãy bắn Signal (core/signals.py) thay vì gọi trực tiếp.

7. 🎨 Giao diện & Frontend (Assets)
[ ] Namespace Consistency: Template phải đặt tại: themes/{theme}/templates/{theme}/modules/{module_name}/.
[ ] Url_for Sync: Cập nhật toàn bộ link trong HTML/JS:
Cũ: url_for('old_blueprint.func') -> Mới: url_for('{module_name}.func')
[ ] Static Paths: Sửa đường dẫn file tĩnh thành: url_for('static', filename='modules/{name}/js/...').
[ ] Variable Mapping: Kiểm tra biến truyền vào template (Jinja2) có khớp với Schema mới không (VD: obj.name hay obj.title?).

8. ⚙️ Cấu hình (Configuration)
[ ] Fallback Chain: Code phải chạy được theo thứ tự ưu tiên: DB Config -> .env -> config.py (Default).
[ ] Default Config: File config.py phải chứa đầy đủ giá trị mặc định để app không crash khi thiếu .env.
[ ] Env Update: Nếu thêm API Key mới, cập nhật ngay vào .env.example.

9. 📝 Tài liệu hóa (Documentation)
Tạo file README.md trong thư mục module với nội dung:
[ ] Description: Module này làm gì?
[ ] Dependency: Nó phụ thuộc vào module nào (VD: cần auth, fsrs)?
[ ] Key Configs: Các biến cấu hình quan trọng.
[ ] Events: Các Signal mà nó lắng nghe (Listen) hoặc phát ra (Emit).

10. 🧹 Dọn dẹp & Kiểm tra cuối (Final Polish)
[ ] Dead Code: Xóa file model cũ ở thư mục ngoài (core/models) sau khi migrate thành công.
[ ] Shadow Logic Cleanup: Tìm và xóa các hàm cũ trùng lặp tính năng ở các module khác.
[ ] Enable Check: Vào Admin -> Modules Management, đảm bảo module hiện lên và trạng thái là Active.
[ ] Smoke Test: Chạy thử 1 luồng chính (Happy Path) để đảm bảo không lỗi import/template.

# Cấu trúc Dự án MindStack

Tài liệu này mô tả cấu trúc thư mục và các thành phần chính của dự án MindStack (phiên bản `newmindstack`).

## 1. Cấu trúc Thư mục Gốc (`newmindstack/`)

Đây là thư mục gốc của ứng dụng backend/web.

```text
newmindstack/
├── .agent/                 # Cấu hình Agent (nếu có)
├── docs/                   # Tài liệu dự án
│   ├── database_schema.md      # Cấu trúc CSDL chi tiết
│   ├── module_relationships.md # Sơ đồ quan hệ module
│   └── project_structure.md    # (File này)
├── migrations/             # Alembic migrations (quản lý thay đổi DB)
├── mindstack_app/          # **MAIN APPLICATION PACKAGE**
├── scripts/                # Các script tiện ích (cài đặt, maintenance)
├── tests/                  # Unit & Integration Tests
├── .env                    # Biến môi trường (Sensitive info)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Các thư viện Python phụ thuộc
└── start_mindstack_app.py  # Entry point chạy ứng dụng
```

---

## 2. Ứng dụng Chính (`mindstack_app/`)

Đây là nơi chứa toàn bộ mã nguồn logic của ứng dụng.

```text
mindstack_app/
├── core/                   # **Infrastructure Core**
│   ├── __init__.py         # Khởi tạo App Factory
│   ├── config.py           # Class cấu hình (Dev, Prod)
│   ├── extensions.py       # Khởi tạo extensions (db, login_manager, celery...)
│   ├── module_registry.py  # Đăng ký tự động các module
│   └── ...                 # Logging, Error handlers
│
├── modules/                # **Feature Modules (Modular Monolith)**
│   ├── auth/               # Xác thực người dùng
│   ├── learning/           # Core logic học tập (Container, Item)
│   ├── AI/                 # Tích hợp AI (Gemini, OpenAI)
│   ├── quiz/               # Module Quiz
│   ├── vocab_flashcard/    # Module Flashcard
│   ├── course/             # Module Khóa học
│   ├── collab/             # Tính năng học nhóm/thi đấu
│   ├── gamification/       # Điểm số, Huy hiệu
│   ├── stats/              # Thống kê, Báo cáo
│   └── ... (Các module khác: notes, history, notification, ops...)
│
├── themes/                 # **Frontend Layer (Templates & Static)**
│   ├── aura/               # Giao diện Desktop chính
│   ├── aura_mobile/        # Giao diện Mobile tối ưu
│   └── admin/              # Giao diện quản trị
│       ├── templates/      # Jinja2 HTML templates
│       └── static/         # CSS, JS, Images, Fonts
│
├── models/                 # **Shared/Legacy Access Models**
│   └── app_settings.py     # Cấu hình ứng dụng lưu trong DB
│
├── services/               # **Cross-Cutting Services**
│   └── (Các service dùng chung nếu không thuộc module nào)
│
├── utils/                  # **Utilities**
│   ├── decorators.py       # Auth decorators, cache decorators
│   ├── helpers.py          # Hàm hỗ trợ chung
│   └── ...
│
└── logics/                 # (Legacy) Business logic cũ chưa refactor hết
```

---

## 3. Chi tiết Module (`mindstack_app/modules/`)

Mỗi module trong thư mục này thường tuân theo cấu trúc chuẩn:

```text
module_name/
├── __init__.py             # Khởi tạo Blueprint
├── models.py               # Định nghĩa Database Models riêng của module
├── routes.py               # API Endpoints & View Controllers
├── services.py             # Business Logic Layer
├── events.py               # Xử lý sự kiện (Signals)
└── templates/              # (Optional) Template riêng nếu cần ghi đè
```

---

## 4. Giao diện & Themes (`mindstack_app/themes/`)

MindStack hỗ trợ đa giao diện (Themeable):

*   **`aura`**: Giao diện mặc định cho Desktop, thiết kế hiện đại, Glassmorphism.
*   **`aura_mobile`**: Giao diện tối ưu trải nghiệm chạm vuốt cho Mobile.
*   **`admin`**: Trang Dashboard quản trị viên.

Cấu trúc trong mỗi Theme folder:
```text
theme_name/
├── templates/              # Chứa các file .html
│   ├── base.html           # Layout chính
│   ├── macros/             # Các component tái sử dụng (Card, Button...)
│   └── index.html          # Trang chủ
└── static/                 # Tài nguyên tĩnh
    ├── css/
    ├── js/
    └── images/
```

---

## 5. File Quan trọng Khác

*   **`start_mindstack_app.py`**:
    *   File chạy chính.
    *   Sử dụng: `python start_mindstack_app.py`
    *   Khởi tạo server Flask (mặc định port 5000).

*   **`.env`**:
    *   Chứa `SECRET_KEY`, `DATABASE_URL`, `AI_API_KEY`...
    *   **Không bao giờ commit file này lên Git.**

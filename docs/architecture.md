# MindStack - Clean Architecture Documentation

> **Phiên bản:** 2.0  
> **Ngày cập nhật:** 29/12/2025  
> **Tác giả:** MindStack Development Team

---

## 📋 Tổng quan

MindStack được xây dựng theo nguyên tắc **Clean Architecture** (kiến trúc sạch), đảm bảo:
- ✅ **Tách biệt trách nhiệm (Separation of Concerns)**
- ✅ **Độc lập với framework** - Logic nghiệp vụ không phụ thuộc vào Flask
- ✅ **Dễ kiểm thử (Testability)** - Mỗi layer có thể test độc lập
- ✅ **Khả năng mở rộng (Scalability)** - Dễ thêm tính năng mới
- ✅ **Bảo trì dễ dàng (Maintainability)** - Code rõ ràng, dễ hiểu

---

## 🏗️ Cấu trúc thư mục Root

```
newmindstack/
│
├── 📁 mindstack_app/          # Main application package
│   ├── core/                  # Application infrastructure
│   ├── models/                # Database models
│   ├── logics/                # Pure business logic
│   ├── services/              # Service layer
│   ├── modules/               # Feature modules
│   ├── static/                # Static assets
│   ├── config.py              # Application configuration
│   ├── extensions.py          # Flask extensions
│   └── __init__.py            # App factory
│
├── 📁 scripts/                # Utility & maintenance scripts
│   ├── db_migrations/         # Database migration scripts
│   └── debug/                 # Debug utilities
│
├── 📁 tests/                  # Test suite
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
│
├── 📁 docs/                   # Documentation
│   ├── architecture.md        # This file
│   └── database_schema.md     # Database documentation
│
├── 📄 start_mindstack_app.py  # Application entry point
├── 📄 requirements.txt        # Production dependencies
├── 📄 .env.example            # Environment variables template
├── 📄 .gitignore              # Git ignore rules
└── 📄 README.md               # Project overview
```

---

## 🎯 Kiến trúc Layers (Từ ngoài vào trong)

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Infrastructure (core/)                │
│  • Flask app initialization                     │
│  • Extensions setup (DB, Login, CSRF...)        │
│  • Module registry & blueprint registration     │
│  • Configuration & logging                      │
└─────────────────────────────────────────────────┘
                      ↓ uses ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: Presentation (modules/)               │
│  • Routes (HTTP handlers)                       │
│  • Request/Response processing                  │
│  • Templates & UI logic                         │
│  • Form validation                              │
└─────────────────────────────────────────────────┘
                      ↓ uses ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: Application Services (services/)      │
│  • Database operations (CRUD)                   │
│  • Transaction management                       │
│  • Cross-module orchestration                   │
│  • Data aggregation                             │
└─────────────────────────────────────────────────┘
                      ↓ uses ↓
┌─────────────────────────────────────────────────┐
│  Layer 4: Domain Logic (logics/)                │
│  • Pure business algorithms                     │
│  • Framework-agnostic logic                     │
│  • Reusable computations                        │
│  • NO database access                           │
└─────────────────────────────────────────────────┘
                      ↓ uses ↓
┌─────────────────────────────────────────────────┐
│  Layer 5: Data Models (models/)                 │
│  • SQLAlchemy models                            │
│  • Database schema definitions                  │
│  • Model relationships                          │
└─────────────────────────────────────────────────┘
```

> **Nguyên tắc quan trọng:** Mỗi layer chỉ phụ thuộc vào layer bên dưới nó.  
> Layer bên trong **KHÔNG BAO GIỜ** biết về sự tồn tại của layer bên ngoài.

---

## 📦 Chi tiết từng Layer

### 1️⃣ **`core/` - Infrastructure Layer**

**Mục đích:** Khởi tạo và cấu hình ứng dụng Flask

**Files chính:**
- `bootstrap.py` - Bootstrap functions cho Flask app
- `module_registry.py` - Auto-registration system cho modules

**Nhiệm vụ:**
```python
# core/bootstrap.py
- configure_logging()          # Setup logging system
- register_extensions()        # Init DB, Login Manager, CSRF, Scheduler
- configure_static_uploads()   # Static file handling
- register_context_processors() # Template context & filters
- register_blueprints()        # Auto-register all modules
- initialize_database()        # Create tables & seed data

# core/module_registry.py
- ModuleDefinition             # Metadata cho modules
- register_modules()           # Dynamic blueprint registration
- DEFAULT_MODULES              # List tất cả modules
```

**Đặc điểm:**
- ⚙️ Chạy **một lần** khi khởi động app
- 🔌 **Dính chặt vào Flask** - framework-specific
- 🌍 **Application-wide** configuration
- ❌ **KHÔNG chứa** business logic

**Ví dụ:**
```python
# core/bootstrap.py
def register_extensions(app: Flask):
    """Infrastructure setup - runs once at startup"""
    db.init_app(app)
    login_manager.init_app(app)
    csrf_protect.init_app(app)
    scheduler.init_app(app)
```

---

### 2️⃣ **`modules/` - Presentation Layer**

**Mục đích:** Xử lý HTTP requests/responses và hiển thị UI

**Cấu trúc module điển hình:**
```
modules/learning/
├── routes.py              # Main blueprint & routes
├── templates/             # Jinja2 templates
├── sub_modules/           # Nested features
│   ├── flashcard/
│   │   ├── routes/        # Feature-specific routes
│   │   ├── services/      # Feature-specific services
│   │   ├── engine.py      # Core logic engine
│   │   └── templates/     # Feature templates
│   └── quiz/
└── shared/                # Shared utilities
```

**Nhiệm vụ:**
- 🌐 Xử lý HTTP requests (GET, POST, PUT, DELETE...)
- 📝 Validate form data
- 🎨 Render templates
- 🔒 Authentication & Authorization checks
- 📊 Format data để hiển thị

**Đặc điểm:**
- 🎯 Feature-focused (mỗi module = 1 tính năng)
- 🔄 Gọi **services/** để thao tác database
- 📦 Modular & reusable
- 🧪 Có thể test bằng integration tests

**Ví dụ:**
```python
# modules/learning/routes.py
@learning_bp.route('/flashcard/<int:set_id>')
@login_required
def flashcard_session(set_id):
    """Route handler - presentation layer"""
    # 1. Validate input
    # 2. Call service layer to get data
    flashcard_data = FlashcardService.get_set_details(set_id)
    # 3. Render template
    return render_template('flashcard/session.html', data=flashcard_data)
```

---

### 3️⃣ **`services/` - Application Service Layer**

**Mục đích:** Quản lý database operations và orchestration

**Files:**
```
services/
├── progress_service.py    # Learning progress CRUD
└── config_service.py      # App configuration CRUD
```

**Nhiệm vụ:**
- 💾 **Database operations** (Create, Read, Update, Delete)
- 🔄 **Transaction management**
- 🎭 **Orchestration** - điều phối nhiều operations
- 📊 **Data aggregation** từ nhiều models
- ✅ **Business validation** trước khi lưu DB

**Đặc điểm:**
- 🗄️ Trực tiếp làm việc với **models/**
- 🎯 Stateless - không lưu trạng thái
- 🔁 Reusable across modules
- 🧪 Test với database mocking

**Ví dụ:**
```python
# services/progress_service.py
class ProgressService:
    """Service layer - handles database operations"""
    
    @staticmethod
    def update_learning_progress(user_id, item_id, quality):
        """Orchestrate database updates"""
        # 1. Get or create progress record
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        
        if not progress:
            progress = LearningProgress(user_id=user_id, item_id=item_id)
            db.session.add(progress)
        
        # 2. Update fields
        progress.last_reviewed = datetime.utcnow()
        progress.review_count += 1
        
        # 3. Commit transaction
        db.session.commit()
        return progress
```

---

### 4️⃣ **`logics/` - Domain Logic Layer** ⭐

**Mục đích:** Pure business logic, framework-agnostic

**Files:**
```
logics/
├── voice_engine.py        # TTS & STT algorithms
└── config_parser.py       # Configuration parsing logic
```

**Nhiệm vụ:**
- 🧠 **Business algorithms** thuần túy
- 🔢 **Calculations** & transformations
- 📐 **Pure functions** - input → output
- 🎯 **Domain-specific logic**
- ❌ **KHÔNG** database, HTTP, templates

**Đặc điểm:**
- 🌟 **Framework-agnostic** - có thể dùng ngoài Flask
- 🧪 **Dễ test** - pure functions
- ♻️ **Highly reusable** - dùng ở CLI, API, background jobs...
- 📦 **No side effects** - không thay đổi state bên ngoài
- ⚡ **Stateless** - không lưu instance variables

**Ví dụ:**
```python
# logics/voice_engine.py
class VoiceEngine:
    """Pure business logic - NO Flask, NO Database"""
    
    def text_to_speech(self, text: str, lang: str = 'en') -> str:
        """Pure algorithm: text → audio file path"""
        if not text or not text.strip():
            raise ValueError("Text content is empty")
        
        # Generate audio using gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        tts.save(temp_path)
        
        return temp_path  # Return path, no database involved
```

**Khi nào tạo logic engine:**
- ✅ Khi có thuật toán phức tạp cần test độc lập
- ✅ Khi logic cần dùng lại ở nhiều nơi (routes, CLI, API...)
- ✅ Khi cần tách biệt business logic khỏi framework
- ✅ Khi có external API calls (Google TTS, Gemini AI...)

---

### 5️⃣ **`models/` - Data Layer**

**Mục đích:** Define database schema và relationships

**Files:**
```
models/
├── user.py                # User & authentication models
├── learning.py            # Learning-related models
├── platform.py            # Platform configuration models
└── __init__.py            # Export all models
```

**Nhiệm vụ:**
- 📊 **SQLAlchemy models** - define tables
- 🔗 **Relationships** giữa các tables
- ✅ **Validation** ở database level
- 🔍 **Query helpers** - custom query methods

**Đặc điểm:**
- 🗄️ Mapping Python objects ↔ Database tables
- 🔒 Define constraints & indexes
- 📝 Model-level validation
- 🎯 Domain entities representation

**Ví dụ:**
```python
# models/learning.py
class LearningProgress(db.Model):
    """Data model - represents database table"""
    __tablename__ = 'learning_progress'
    
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'))
    learning_mode = db.Column(db.String(50))
    due_time = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='progress_records')
    item = db.relationship('LearningItem', backref='progress_records')
```

---

## 🔄 Data Flow Example

Ví dụ: User học flashcard và submit câu trả lời

```
1. Browser → POST /learn/flashcard/answer
                ↓
2. modules/learning/routes.py (Presentation)
   @learning_bp.route('/flashcard/answer', methods=['POST'])
   def submit_answer():
       # Validate request
       quality = request.form.get('quality')
       item_id = request.form.get('item_id')
                ↓
3. modules/learning/sub_modules/flashcard/engine.py (Domain Logic)
   FlashcardEngine.process_answer(user_id, item_id, quality)
       # Calculate SRS values using pure algorithm
       new_interval = calculate_sm2_interval(quality, current_interval)
                ↓
4. services/progress_service.py (Service)
   ProgressService.update_progress(user_id, item_id, new_interval)
       # Save to database
                ↓
5. models/learning.py (Data)
   LearningProgress object updated
                ↓
6. Database transaction committed
                ↓
7. Response ← Back to browser (JSON or HTML)
```

---

## 🎯 Nguyên tắc thiết kế

### ✅ DO (Nên làm)

1. **Dependency Rule** - Chỉ phụ thuộc vào layer bên trong
   ```python
   ✅ routes.py → service.py → engine.py → models.py
   ❌ models.py → service.py (KHÔNG BAO GIỜ)
   ```

2. **Single Responsibility** - Mỗi file/class có 1 trách nhiệm
   ```python
   ✅ FlashcardEngine → Chỉ xử lý flashcard logic
   ✅ ProgressService → Chỉ thao tác progress records
   ```

3. **Pure Functions trong logics/**
   ```python
   ✅ def calculate_score(current, quality) -> int:
       """No side effects, deterministic"""
       return current + (quality * 10)
   ```

4. **Service Layer cho DB operations**
   ```python
   ✅ ProgressService.create_progress(...)  # Trong service
   ❌ db.session.add(...) trong routes.py   # TRÁNH
   ```

5. **Separation of Concerns**
   ```python
   ✅ Routes → User input/output
   ✅ Services → Database operations
   ✅ Logics → Algorithms
   ✅ Models → Data structure
   ```

### ❌ DON'T (Tránh làm)

1. ❌ **Business logic trong routes**
   ```python
   # BAD - routes.py
   @bp.route('/calculate')
   def calculate():
       result = complex_calculation()  # ← Logic ở đây!
   
   # GOOD - routes.py
   @bp.route('/calculate')
   def calculate():
       result = CalculationEngine.compute()  # ← Logic ở engine
   ```

2. ❌ **Database trong logics/**
   ```python
   # BAD - logics/engine.py
   def process(user_id):
       user = User.query.get(user_id)  # ← NO DB!
   
   # GOOD - logics/engine.py
   def process(user_data: dict):
       return compute(user_data)  # ← Pure function
   ```

3. ❌ **Framework-specific code trong logics/**
   ```python
   # BAD - logics/engine.py
   from flask import request  # ← NO Flask!
   
   # GOOD - logics/engine.py
   # No framework imports at all
   ```

4. ❌ **Tạo quá nhiều layers không cần thiết**
   ```python
   # BAD - Quá phức tạp
   routes → controller → facade → service → repository → model
   
   # GOOD - Đủ dùng
   routes → service → model
   ```

---

## 📁 Module Structure Pattern

Mọi module trong `modules/` nên tuân theo cấu trúc này:

```
modules/{module_name}/
│
├── __init__.py                # Export blueprint
├── routes.py                  # Main routes (hoặc routes/)
│
├── services/                  # Service layer (optional)
│   └── {module}_service.py
│
├── logics/                    # Domain logic (optional)
│   └── {module}_engine.py
│
├── templates/                 # Jinja2 templates
│   └── {module}/
│       ├── index.html
│       └── _partials/
│
├── static/                    # Module-specific static files (optional)
│   ├── css/
│   ├── js/
│   └── images/
│
└── sub_modules/               # Nested features (optional)
    └── {sub_feature}/
        ├── routes/
        ├── services/
        └── templates/
```

**Ví dụ áp dụng:**
```
modules/learning/
├── routes.py                  # Main learning routes
├── sub_modules/
│   ├── flashcard/
│   │   ├── engine.py          # FlashcardEngine (pure logic)
│   │   ├── routes/            # HTTP handlers
│   │   ├── services/          # Database operations
│   │   └── templates/
│   └── quiz/
│       ├── engine.py          # QuizEngine (pure logic)
│       └── routes/
└── templates/
```

---

## 🧪 Testing Strategy

### Unit Tests (logics/)
```python
# tests/unit/test_voice_engine.py
def test_text_to_speech():
    """Test pure logic - no Flask, no DB"""
    engine = VoiceEngine()
    result = engine.text_to_speech("Hello", lang="en")
    assert os.path.exists(result)
    assert result.endswith('.mp3')
```

### Integration Tests (modules/)
```python
# tests/integration/test_flashcard_flow.py
def test_flashcard_session(client, auth):
    """Test full flow with test database"""
    auth.login()
    response = client.post('/learn/flashcard/answer', data={
        'item_id': 1,
        'quality': 5
    })
    assert response.status_code == 200
```

### Service Tests
```python
# tests/unit/test_progress_service.py
def test_update_progress(app, db_session):
    """Test service layer with database"""
    with app.app_context():
        progress = ProgressService.update_progress(
            user_id=1, item_id=1, quality=5
        )
        assert progress.review_count == 1
```

---

## 🚀 Best Practices

### 1. **Import Guidelines**

```python
# ✅ GOOD - Clear layer separation
# routes.py
from ..services.flashcard_service import FlashcardService
from ..engine import FlashcardEngine

# services/flashcard_service.py
from ...models import LearningProgress, LearningItem

# logics/voice_engine.py
# NO imports from other layers!
from gtts import gTTS  # External library only
```

### 2. **Error Handling**

```python
# routes.py - User-friendly messages
@bp.route('/flashcard/<int:set_id>')
def session(set_id):
    try:
        data = FlashcardService.get_set(set_id)
    except NotFoundError:
        flash('Bộ thẻ không tồn tại', 'error')
        return redirect(url_for('learning.dashboard'))

# services/ - Raise specific exceptions
class FlashcardService:
    @staticmethod
    def get_set(set_id):
        flashcard_set = LearningContainer.query.get(set_id)
        if not flashcard_set:
            raise NotFoundError(f"Set {set_id} not found")
        return flashcard_set

# logics/ - Validate inputs
class VoiceEngine:
    def text_to_speech(self, text: str):
        if not text or not text.strip():
            raise ValueError("Text content is empty")
```

### 3. **Naming Conventions**

```python
# Routes
flashcard_session()         # verb_noun pattern
create_flashcard_set()
update_progress()

# Services
FlashcardService            # {Feature}Service
ProgressService
class methods: create(), update(), delete(), get()

# Logics/Engines
FlashcardEngine             # {Feature}Engine
VoiceEngine
class methods: process(), calculate(), generate()

# Models
LearningProgress            # PascalCase, singular
User, LearningItem
```

### 4. **Code Organization**

```python
# Routes file structure
"""Module docstring"""

# 1. Imports
from flask import Blueprint, render_template
from .services import MyService

# 2. Blueprint definition
my_bp = Blueprint('my_module', __name__)

# 3. Helper functions (private)
def _validate_input(data):
    pass

# 4. Route handlers (public)
@my_bp.route('/')
def index():
    pass
```

---

## 📚 Tài liệu tham khảo

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Flask Application Patterns](https://flask.palletsprojects.com/en/latest/patterns/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)

---

## 🔧 Migration Guide

Nếu bạn có code cũ không theo Clean Architecture:

### Before (Anti-pattern ❌)
```python
# routes.py - Everything in one place!
@bp.route('/flashcard/answer')
def submit_answer():
    # Business logic
    if quality == 0:
        interval = 1
    elif quality == 5:
        interval = current * 2.5
    
    # Database operation
    progress = LearningProgress.query.get(progress_id)
    progress.interval = interval
    db.session.commit()
    
    # Response
    return jsonify({'success': True})
```

### After (Clean Architecture ✅)
```python
# routes.py - Just HTTP handling
@bp.route('/flashcard/answer')
def submit_answer():
    quality = request.json.get('quality')
    result = FlashcardEngine.process_answer(
        user_id=current_user.user_id,
        item_id=item_id,
        quality=quality
    )
    return jsonify(result)

# engine.py - Pure business logic
class FlashcardEngine:
    @staticmethod
    def process_answer(user_id, item_id, quality):
        # Calculate using SM-2 algorithm
        new_interval = SRSAlgorithm.calculate_interval(quality)
        
        # Update via service
        ProgressService.update_progress(
            user_id, item_id, new_interval
        )
        return {'success': True, 'interval': new_interval}

# services/progress_service.py - Database operations
class ProgressService:
    @staticmethod
    def update_progress(user_id, item_id, interval):
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        progress.interval = interval
        db.session.commit()
        return progress
```

---

## ✅ Checklist khi thêm tính năng mới

- [ ] Tạo blueprint trong `modules/`
- [ ] Routes chỉ handle HTTP, không có business logic
- [ ] Logic phức tạp vào `logics/` hoặc `engine.py`
- [ ] Database operations vào `services/`
- [ ] Models đã có relationships và constraints
- [ ] Có unit tests cho logic layer
- [ ] Có integration tests cho routes
- [ ] Documentation đã update

---

## 📝 Ghi chú quan trọng

1. **Không phải mọi module đều cần đầy đủ các layers**
   - Module đơn giản chỉ cần: routes + templates
   - Module phức tạp mới cần: routes + services + logics + templates

2. **Service layer là optional**
   - Nếu chỉ CRUD đơn giản, routes có thể gọi model trực tiếp
   - Nếu có orchestration, business validation → cần service

3. **Logics layer là optional**
   - Chỉ tạo khi có algorithm phức tạp cần test riêng
   - Hoặc khi logic cần reuse ở nhiều nơi (CLI, API, background jobs)

4. **Ưu tiên đơn giản hóa**
   - Đừng over-engineer
   - Bắt đầu đơn giản, refactor sau khi cần
   - Clean Architecture là guidelines, không phải rules cứng nhắc

---

**Happy Coding! 🚀**

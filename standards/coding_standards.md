# 📋 MindStack Coding Standards

## Table of Contents
1. [Clean Architecture](#clean-architecture)
2. [Template Structure](#template-structure)
3. [Module Organization](#module-organization)
4. [Naming Conventions](#naming-conventions)

---

## 1. Clean Architecture

### 🎯 3-Layer Architecture

```
module/
├── logics/          # Pure business logic (NO database)
├── services/        # Database + orchestration
└── routes.py        # HTTP endpoints
    └── api_routes/  # REST API endpoints
```

### Layer 1: `logics/` - Pure Logic

**Mục đích**: Thuật toán thuần túy, tính toán, business rules

**Quy tắc**:
- ❌ **KHÔNG ĐƯỢC** import `db`, `models`, `flask`
- ❌ **KHÔNG ĐƯỢC** database queries
- ✅ Chỉ tính toán, xử lý data
- ✅ Stateless, pure functions
- ✅ Dễ test (unit test)

**Ví dụ**:
```python
# logics/unified_srs.py
class UnifiedSrsSystem:
    @staticmethod
    def process_answer(current_status, current_interval, quality):
        """Pure calculation - NO database"""
        # Calculate next interval
        new_interval = current_interval * (quality / 3)
        
        # Calculate memory power
        mastery = calculate_mastery(current_status, quality)
        
        return SrsResult(
            next_interval=new_interval,
            mastery=mastery
        )
```

### Layer 2: `services/` - Database Layer

**Mục đích**: CRUD operations, gọi logics, lưu database

**Quy tắc**:
- ✅ Import `db`, `models`
- ✅ Database queries
- ✅ Gọi functions từ `logics/`
- ✅ Orchestration (kết hợp nhiều operations)
- ❌ **KHÔNG ĐƯỢC** chứa business logic phức tạp

**Ví dụ**:
```python
# services/srs_service.py
class SrsService:
    @staticmethod
    def update_unified(user_id, item_id, quality):
        """Fetch from DB → Call logic → Save to DB"""
        # 1. Fetch from database
        progress = LearningProgress.query.get(...)
        
        # 2. Call pure logic
        result = UnifiedSrsSystem.process_answer(
            current_status=progress.status,
            quality=quality
        )
        
        # 3. Save to database
        progress.interval = result.next_interval
        progress.mastery = result.mastery
        db.session.commit()
        
        return progress, result
```

### Layer 3: `routes.py` & `api_routes/` - HTTP Layer

**Mục đích**: Nhận HTTP requests, gọi services, trả về response

**Quy tắc**:
- ✅ Import `Flask`, `Blueprint`
- ✅ Gọi `services/` để xử lý logic
- ✅ Validate input
- ✅ Format output (JSON hoặc HTML)
- ❌ **KHÔNG ĐƯỢC** business logic
- ❌ **KHÔNG ĐƯỢC** database queries trực tiếp

#### `routes.py` - HTML Pages & Blueprint Registration

```python
# routes.py
from flask import Blueprint, render_template
from .api_routes import stats_api_bp

stats_bp = Blueprint('stats', __name__, 
                    url_prefix='/stats',
                    template_folder='templates')

# Register API routes
stats_bp.register_blueprint(stats_api_bp)

@stats_bp.route('/dashboard')
def dashboard():
    """HTML page - render template"""
    return render_template('stats/dashboard/default/index.html')

@stats_bp.route('/dashboard/data')
def dashboard_data():
    """JSON API - for AJAX"""
    stats = SrsService.get_container_stats(user_id, container_id)
    return jsonify(stats)
```

#### `api_routes/` - REST API Endpoints

```python
# api_routes/stats_api.py
stats_api_bp = Blueprint('stats_api', __name__, 
                        url_prefix='/api/learning/stats')

@stats_api_bp.route('/item/<int:item_id>')
def get_item_stats(item_id):
    """REST API - Returns JSON only"""
    stats = SrsService.get_item_stats(item_id)
    return jsonify(stats)
```

---

## 2. Template Structure

### 📁 Folder Structure

**Pattern có 2 loại:**

#### **A) Dashboard Templates** (Vocabulary, Quiz)
- **Single file** với responsive CSS

```
module/templates/
└── module_name/
    └── dashboard/
        └── default/
            └── index.html    # SINGLE FILE (responsive @media)
```

#### **B) Session/Interactive Templates** (Flashcard, Quiz Session)
- **Separate files** cho mobile & desktop

```
module/templates/
└── module_name/
    └── feature/
        └── default/
            ├── index.html           # Main orchestrator
            ├── _mobile.html         # Mobile UI
            ├── _desktop.html        # Desktop UI
            ├── _card_mobile.html    # Card component (mobile)
            ├── _card_desktop.html   # Card component (desktop)
            ├── _stats_mobile.html   # Stats modal (mobile)
            └── _stats_desktop.html  # Stats panel (desktop)
```

**Ví dụ thực tế**:
```
flashcard/individual/cardsession/default/
├── index.html           ← Main file
├── _mobile.html         ← Mobile layout
├── _desktop.html        ← Desktop layout
├── _card_mobile.html
├── _card_desktop.html
├── _stats_mobile.html
└── _stats_desktop.html

quiz/individual/session/default/
├── index.html
├── _quiz_session_batch_mobile.html
└── _quiz_session_batch_desktop.html
```

### 📱 Template Patterns

#### **Pattern 1: Single File (Dashboard)**

Dùng cho: Vocabulary dashboard, Quiz dashboard, Stats dashboard

```html
<!-- index.html -->
{% extends "base.html" %}

{% block extra_css %}
<style>
    /* Mobile-first base styles */
    .container {
        padding: 1rem;
    }

    /* Mobile specific */
    @media (max-width: 1023px) {
        body > header,
        body > footer {
            display: none !important;
        }

        .step {
            position: fixed;
            inset: 0;
        }
    }

    /* Desktop specific */
    @media (min-width: 1024px) {
        .container {
            max-width: 1200px;
            padding: 2rem;
        }

        .desktop-grid {
            display: grid;
            grid-template-columns: 1fr 400px;
        }
    }
</style>
{% endblock %}

{% block content %}
<!-- Same HTML for both mobile & desktop -->
<div class="container">
    <!-- Content -->
</div>
{% endblock %}
```

#### **Pattern 2: Separate Files (Session/Interactive)**

Dùng cho: Flashcard session, Quiz session, Interactive features

**`index.html` - Orchestrator:**
```html
{% extends "base.html" %}

{% block content %}
{# Include cả mobile và desktop - CSS sẽ hide/show #}
{% include template_base_path ~ '/_mobile.html' %}
{% include template_base_path ~ '/_desktop.html' %}

{# Shared components #}
{% include template_base_path ~ '/_stats_mobile.html' %}
{% endblock %}
```

**`_mobile.html` - Mobile UI:**
```html
{# Mobile-only structure #}
<div class="mobile-container">
    {# Full mobile UI here #}
    {% include template_base_path ~ '/_card_mobile.html' %}
</div>

<style>
    .mobile-container {
        display: block;
    }

    @media (min-width: 1024px) {
        .mobile-container {
            display: none !important;
        }
    }
</style>
```

**`_desktop.html` - Desktop UI:**
```html
{# Desktop-only structure #}
<div class="desktop-container">
    {# Full desktop UI here #}
    {% include template_base_path ~ '/_card_desktop.html' %}
</div>

<style>
    .desktop-container {
        display: none;
    }

    @media (min-width: 1024px) {
        .desktop-container {
            display: block !important;
        }
    }
</style>
```

### 🎯 Khi Nào Dùng Pattern Nào?

| Feature Type | Pattern | Files |
|--------------|---------|-------|
| **Dashboard** (Browse, List) | Single File | `index.html` only |
| **Session** (Learning, Practice) | Separate Files | `index.html` + `_mobile.html` + `_desktop.html` |
| **Interactive** (Complex UI) | Separate Files | Multiple partials |
| **Simple Page** (Detail, Form) | Single File | `index.html` only |

### 📋 Template Include Pattern

```python
# routes.py
@bp.route('/session')
def session():
    template_base_path = 'flashcard/individual/cardsession/default'
    return render_template(
        f'{template_base_path}/index.html',
        template_base_path=template_base_path  # Pass to template
    )
```

```jinja
<!-- index.html -->
{% include template_base_path ~ '/_mobile.html' %}
{% include template_base_path ~ '/_desktop.html' %}
```

### 🎨 Template Best Practices

1. **Inline CSS & JS**
   - CSS trong `{% block extra_css %}`
   - JavaScript trong `{% block extra_js %}`

2. **Mobile-First Approach**
   - Base styles cho mobile
   - `@media (min-width: ...)` cho desktop

3. **Hide Navbar on Mobile**
   ```css
   @media (max-width: 1023px) {
       body > header, 
       body > footer {
           display: none !important;
       }
   }
   ```

4. **Responsive Grids**
   ```css
   .grid {
       grid-template-columns: repeat(2, 1fr);  /* Mobile: 2 cols */
   }
   
   @media (min-width: 640px) {
       .grid {
           grid-template-columns: repeat(3, 1fr);  /* Tablet: 3 cols */
       }
   }
   
   @media (min-width: 1024px) {
       .grid {
           grid-template-columns: repeat(4, 1fr);  /* Desktop: 4 cols */
       }
   }
   ```

---

## 3. Module Organization

### 📦 Sub-Module Structure

```
modules/learning/
├── __init__.py              # Export learning_bp
├── routes.py                # Register all sub-modules
├── logics/                  # Shared logic
├── services/                # Shared services
└── sub_modules/
    ├── vocabulary/
    │   ├── __init__.py      # Export vocabulary_bp
    │   ├── routes.py        # HTML routes
    │   ├── api_routes/      # API endpoints (if needed)
    │   ├── templates/
    │   │   └── vocabulary/
    │   │       └── dashboard/
    │   │           └── default/
    │   │               └── index.html
    │   ├── logics/          # Vocab-specific logic (optional)
    │   └── services/        # Vocab-specific services (optional)
    │
    ├── stats/
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── api_routes/
    │   │   └── stats_api.py
    │   └── templates/
    │       └── stats/
    │           └── dashboard/
    │               └── default/
    │                   └── index.html
    │
    └── quiz/
        └── ... (giống vocabulary)
```

### 🔧 Module Initialization Pattern

**`sub_modules/stats/__init__.py`**:
```python
from .routes import stats_bp

__all__ = ['stats_bp']
```

**`sub_modules/stats/routes.py`**:
```python
from flask import Blueprint
from .api_routes import stats_api_bp  # Import API routes

# Main blueprint
stats_bp = Blueprint('stats', __name__, 
                    url_prefix='/stats',
                    template_folder='templates')

# Register API sub-blueprint
stats_bp.register_blueprint(stats_api_bp)

# HTML routes
@stats_bp.route('/dashboard')
def dashboard():
    return render_template('stats/dashboard/default/index.html')
```

**`modules/learning/routes.py`** (Parent):
```python
from flask import Blueprint
from .sub_modules.stats import stats_bp
from .sub_modules.vocabulary import vocabulary_bp

learning_bp = Blueprint('learning', __name__)

# Register all sub-modules
learning_bp.register_blueprint(stats_bp)
learning_bp.register_blueprint(vocabulary_bp)
```

---

## 4. Naming Conventions

### File Names
- **Python**: `snake_case.py`
  - `srs_service.py`
  - `unified_srs.py`
  - `stats_api.py`

- **Templates**: `lowercase.html`
  - `index.html`
  - `dashboard.html`

### Class Names
- **PascalCase**
  - `UnifiedSrsSystem`
  - `SrsService`
  - `MemoryEngine`

### Function Names
- **snake_case**
  - `process_answer()`
  - `calculate_batch_stats()`
  - `get_item_stats()`

### Blueprint Names
- **snake_case** (internal name)
- **URL prefix**: `/kebab-case` hoặc `/lowercase`

```python
# Good
stats_bp = Blueprint('stats', __name__, url_prefix='/stats')
vocab_flashcard_bp = Blueprint('vocab_flashcard', __name__, url_prefix='/flashcard')

# Acceptable
stats_api_bp = Blueprint('stats_api', __name__, url_prefix='/api/learning/stats')
```

### CSS Class Names
- **kebab-case**
  - `.vocab-header`
  - `.stat-card`
  - `.distribution-chart`

### JavaScript Variables
- **camelCase**
  - `loadDashboardData()`
  - `updateOverallStats()`

---

## 📚 Quick Reference

### When to Create New...

**New Logic File (`logics/`)**:
- Khi có thuật toán mới (SRS, scoring, calculations)
- Khi cần tách business logic ra khỏi service

**New Service File (`services/`)**:
- Khi cần CRUD operations mới
- Khi thêm tính năng cần tương tác DB

**New API Route (`api_routes/`)**:
- Khi cần REST API endpoint trả về JSON
- Khi frontend cần fetch data (AJAX)

**New HTML Route (`routes.py`)**:
- Khi thêm page mới render HTML
- Khi cần dashboard, form, detail page

**New Sub-Module**:
- Khi thêm feature lớn (vocabulary, quiz, flashcard)
- Khi cần isolated logic + routes + templates

---

## ✅ Checklist for New Features

- [ ] Logic thuần túy trong `logics/` (no DB)
- [ ] Service layer gọi logic + save DB
- [ ] Routes gọi services (không có business logic)
- [ ] Template SINGLE FILE với responsive CSS
- [ ] Mobile-first approach (@media queries)
- [ ] Blueprint registered correctly
- [ ] URL prefix consistent
- [ ] Naming conventions followed

---

## 🎯 TLDR

1. **Clean Architecture**: `logics` (pure) → `services` (DB) → `routes` (HTTP)
2. **Templates**: Single `index.html` với responsive CSS (NO separate mobile/desktop files)
3. **Modules**: Sub-modules dưới `sub_modules/`, mỗi cái có `__init__.py` + `routes.py`
4. **API**: Tách `api_routes/` cho JSON endpoints
5. **Responsive**: `@media (max-width: 1023px)` for mobile, `@media (min-width: 1024px)` for desktop

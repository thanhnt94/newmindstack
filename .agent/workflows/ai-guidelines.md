---
description: AI Guidelines - Quy tắc bắt buộc khi AI làm việc với MindStack project
---

# 🤖 MindStack AI Guidelines

Bộ quy tắc bắt buộc cho AI khi làm việc trên dự án MindStack.

---

## 📋 CHECKLIST SAU MỖI THAY ĐỔI

Sau khi hoàn thành bất kỳ thay đổi code nào, AI **PHẢI** thực hiện:

### 1. Testing (Bắt buộc cho logic changes)
```bash
# Chạy tests liên quan
python -m pytest tests/ -v -k "test_related_name"

# Nếu thay đổi SRS logic
python -m pytest tests/test_srs_logic.py -v

# Nếu thay đổi API
python -m pytest tests/test_stats_api.py -v
```

### 2. Documentation Updates
- [ ] Cập nhật `docs/CHANGELOG.md` nếu là feature/fix quan trọng
- [ ] Cập nhật `docs/API.md` nếu thêm/sửa endpoint
- [ ] Cập nhật `docs/DATABASE.md` nếu thay đổi schema
- [ ] Cập nhật docstrings trong code

### 3. Verification
- [ ] Kiểm tra ứng dụng vẫn chạy: `python start_mindstack_app.py`
- [ ] Kiểm tra không có lỗi console trong browser (nếu UI change)

---

## 🏗️ CẤU TRÚC MODULE BẮT BUỘC

### 3-Layer Architecture

```
module/
├── logics/          # Layer 1: Pure logic (NO DB, NO Flask)
├── services/        # Layer 2: DB + orchestration
├── routes.py        # Layer 3: HTTP endpoints
└── api_routes/      # Layer 3: REST API
```

### Quy tắc từng Layer

| Layer | ✅ Được phép | ❌ Không được |
|-------|-------------|--------------|
| `logics/` | Pure functions, calculations | import db, models, flask |
| `services/` | DB queries, gọi logics | Business logic phức tạp |
| `routes.py` | Gọi services, validate input | DB queries trực tiếp |

---

## 📁 TEMPLATE STRUCTURE (V4)

> **Reference**: `mindstack_app/templates/v4/`  
> **Module Example**: `mindstack_app/templates/v4/pages/learning/vocabulary/dashboard/`

---

### 🗂️ CẤU TRÚC THƯ MỤC GỐC

```
templates/v4/
├── base.html                    # Main base template - EXTENDS this
├── _base_desktop.html           # Desktop layout macros (header/footer)
├── _base_mobile.html            # Mobile layout macros (css reset)
├── includes/                    # Reusable global components
│   ├── assets/                  # Scripts & styles (_global_styles.html, _app_logic.html)
│   ├── modals/                  # Global modals
│   ├── navbar/                  # Navigation components
│   ├── notification/            # Toast/notification components
│   └── ...
└── pages/                       # Page-specific templates
    └── [category]/              # e.g., learning, auth, analytics
        └── [module]/            # e.g., vocabulary, quiz, flashcard
            └── [page_type]/     # e.g., dashboard, session, setup
```

---

### 📄 CẤU TRÚC MODULE TEMPLATE

#### Dashboard/Complex Pages (Vocabulary Dashboard Example)
```
pages/learning/vocabulary/dashboard/
├── index.html                   # 🔑 Entry point - extends base.html
├── detail.html                  # Separate page (optional)
├── _mobile.html                 # Mobile-specific view (partial)
├── _desktop.html                # Desktop-specific view (partial)
├── _*.html                      # Other partials (prefix với _)
├── css/                         # 📦 External CSS
│   ├── dashboard.css            # Main styles
│   ├── dashboard-mobile.css     # Mobile-specific overrides
│   ├── dashboard-desktop.css    # Desktop-specific overrides
│   └── [feature].css            # Feature-specific styles
├── js/                          # 📦 External JavaScript
│   ├── dashboard.js             # Main logic
│   └── [feature].js             # Feature-specific logic
└── components/                  # 📦 Reusable sub-components
    ├── modals/                  # Page-specific modals
    │   ├── _container_stats_modal.html
    │   ├── _edit_set_modal.html
    │   └── _settings_modal.html
    ├── stats/                   # Stats-related components
    │   └── _item_stats_charts.html
    └── steps/                   # Step/wizard components
        ├── _detail_desktop.html
        ├── _detail_mobile.html
        └── _modes.html
```

#### Session/Interactive Pages (Quiz Session Example)
```
pages/learning/quiz/individual/session/
├── index.html                   # Entry point
├── _base.html                   # Session base (if needed)
├── _session_single.html         # Single-item session
├── _session_batch.html          # Batch session
├── _single_mobile.html          # Single mobile view
├── _single_desktop.html         # Single desktop view
├── _batch_mobile.html           # Batch mobile view
├── _batch_desktop.html          # Batch desktop view
├── css/                         # External CSS
├── js/                          # External JavaScript
├── components/                  # Reusable components
├── mobile/                      # Mobile-only templates (optional)
├── desktop/                     # Desktop-only templates (optional)
└── shared/                      # Shared between mobile/desktop
```

---

### 📌 QUY TẮC NAMING FILES

| Loại File | Quy tắc | Ví dụ |
|-----------|---------|-------|
| **Entry point** | `index.html` | `dashboard/index.html` |
| **Separate page** | `[name].html` | `detail.html`, `settings.html` |
| **Partial/Include** | `_[name].html` (prefix `_`) | `_mobile.html`, `_stats_modal.html` |
| **Mobile view** | `_[name]_mobile.html` hoặc `_mobile.html` | `_detail_mobile.html` |
| **Desktop view** | `_[name]_desktop.html` hoặc `_desktop.html` | `_detail_desktop.html` |
| **CSS files** | `[name].css`, `[name]-mobile.css` | `dashboard.css`, `dashboard-mobile.css` |
| **JS files** | `[name].js` | `dashboard.js`, `dashboard_detail.js` |

---

### 🔗 TEMPLATE INHERITANCE & VERSION

#### Sử dụng `template_version` Variable
```jinja
{# Auto-detect version từ context hoặc fallback #}
{% set _v = template_version|default('v4') %}

{# Extends base #}
{% extends _v ~ '/base.html' %}

{# Include với dynamic version #}
{% include _v ~ '/includes/assets/_markdown_assets.html' %}
```

#### Import Macros
```jinja
{% from _v ~ '/includes/navbar/_navbar.html' import render_navbar %}
{% import _v ~ '/_base_desktop.html' as desktop %}
{% import _v ~ '/_base_mobile.html' as mobile %}
```

---

### 📱 RESPONSIVE VIEWS

#### Pattern 1: Conditional Include (Server-side)
```jinja
{# Dùng Jinja condition để render view phù hợp #}
{% if is_mobile %}
    {% include template_base_path ~ '/_mobile.html' %}
{% else %}
    {% include template_base_path ~ '/_desktop.html' %}
{% endif %}
```

#### Pattern 2: CSS-based Show/Hide (Client-side)
```html
{# Render cả 2 views, dùng CSS để ẩn/hiện #}
<div class="hidden lg:block">
    {% include '_desktop.html' %}
</div>
<div class="lg:hidden">
    {% include '_mobile.html' %}
</div>
```

#### Pattern 3: Full-screen Mobile Steps
```css
/* Mobile: Full-screen overlay steps */
@media (max-width: 1023px) {
    .vocab-step {
        display: none;
        position: fixed;
        inset: 0;
        z-index: 100;
        background: #f8fafc;
    }
    .vocab-step.active {
        display: flex;
    }
}

/* Desktop: Normal flow */
@media (min-width: 1024px) {
    .vocab-step {
        display: none !important;
    }
    .vocab-step.active {
        display: block !important;
    }
}
```

---

### 🎨 CSS ORGANIZATION

#### 1. CSS File Naming Convention
```
css/
├── [module].css              # Base styles (applies to all)
├── [module]-mobile.css       # Mobile overrides (@media max-width)
├── [module]-desktop.css      # Desktop overrides (@media min-width)
└── [feature].css             # Feature-specific styles
```

#### 2. Mobile-first Approach
```css
/* Base styles = Mobile */
.card {
    padding: 0.75rem;
    font-size: 0.875rem;
}

/* Desktop overrides */
@media (min-width: 1024px) {
    .card {
        padding: 1.5rem;
        font-size: 1rem;
    }
}
```

#### 3. Include CSS trong Template
```jinja
{% block head %}
{{ super() }}
<style>
    {% include template_base_path ~ '/css/dashboard.css' %}
    {% include template_base_path ~ '/css/dashboard-mobile.css' %}
</style>
{% endblock %}
```

---

### ⚡ JAVASCRIPT ORGANIZATION

#### 1. JS File Structure
```
js/
├── [module].js               # Main logic & initialization
├── [feature].js              # Feature-specific logic
└── [module]_[feature].js     # Combined naming
```

#### 2. Patterns for JS in Templates

**Pattern A: External File Include**
```jinja
{% block scripts %}
<script>
    {% include template_base_path ~ '/js/dashboard.js' %}
</script>
{% endblock %}
```

**Pattern B: Inline with Configuration**
```jinja
<script>
    const CONFIG = {
        apiUrl: '{{ url_for("vocab_api.get_sets") }}',
        csrfToken: '{{ csrf_token() }}',
        userId: {{ current_user.id }}
    };
</script>
<script>
    {% include template_base_path ~ '/js/dashboard.js' %}
</script>
```

#### 3. IIFE Pattern (Avoid Global Pollution)
```javascript
(function() {
    'use strict';
    // All code here
    document.addEventListener('DOMContentLoaded', function() {
        init();
    });
})();
```

---

### 🧩 COMPONENTS ORGANIZATION

#### 1. Subdirectory Structure
```
components/
├── modals/                   # Modal dialogs
│   ├── _[name]_modal.html
│   └── _container_stats_modal.html
├── stats/                    # Statistics displays
│   ├── _item_stats_charts.html
│   └── _inject_stats_button.html
├── steps/                    # Wizard/step components
│   ├── _step_[name].html
│   └── _modes.html
├── cards/                    # Card components
└── forms/                    # Form components
```

#### 2. Component Naming Convention
- Modal: `_[name]_modal.html` hoặc `_container_[name]_modal.html`
- Stats: `_[name]_stats.html` hoặc `_item_stats_[type].html`
- Steps: `_step_[number/name].html` hoặc `_detail_[device].html`

#### 3. Include Components
```jinja
{# Include from components subdirectory #}
{% include template_base_path ~ '/components/modals/_settings_modal.html' %}
{% include template_base_path ~ '/components/stats/_item_stats_charts.html' %}
```

---

### 🚫 QUY TẮC BẮT BUỘC

| ✅ Được phép | ❌ Không được |
|-------------|---------------|
| Đặt templates trong `templates/v4/pages/` | Đặt templates trong `modules/` |
| Dùng `_` prefix cho partials | Đặt tên partial không có prefix |
| Tách CSS/JS ra external files | Inline CSS/JS dài > 50 dòng |
| Dùng `template_version` variable | Hardcode version trong path |
| Mobile-first CSS | Desktop-first CSS |
| Tổ chức components theo chức năng | Để tất cả components flat |

---

### 📋 CHECKLIST TẠO MODULE MỚI

- [ ] Tạo thư mục trong `templates/v4/pages/[category]/[module]/`
- [ ] Tạo `index.html` extends `v4/base.html`
- [ ] Set `{% set _v = template_version|default('v4') %}`
- [ ] Tạo `_mobile.html` và `_desktop.html` nếu cần responsive views
- [ ] Tạo `css/` và `js/` subdirectories cho external assets
- [ ] Tạo `components/` với subdirs (modals/, stats/, etc.) nếu có components
- [ ] Dùng `_` prefix cho tất cả partial files
- [ ] Test responsive trên cả mobile và desktop

---

## 📝 NAMING CONVENTIONS

| Type | Convention | Example |
|------|------------|---------|
| Python files | snake_case | `srs_service.py` |
| Classes | PascalCase | `UnifiedSrsSystem` |
| Functions | snake_case | `process_answer()` |
| Templates | lowercase | `index.html` |
| CSS classes | kebab-case | `.card-header` |
| JS variables | camelCase | `loadDashboardData()` |
| Blueprints | snake_case | `stats_bp` |

---

## 🔄 GIT COMMIT CONVENTIONS

```
feat: add voice pronunciation scoring
fix: correct SRS interval calculation
refactor: extract common template components
docs: update API documentation
test: add gamification scoring tests
style: format code with black
chore: update dependencies
```

---

## ⚠️ QUY TẮC QUAN TRỌNG

### 1. Không tự ý xóa code
- Luôn hỏi trước khi xóa files/functions
- Backup hoặc comment trước khi xóa

### 2. Không thay đổi database schema mà không thông báo
- Schema changes cần migration plan
- Backup database trước khi migrate

### 3. Không hardcode values
```python
# ❌ Sai
points = 10

# ✅ Đúng
points = current_app.config.get('BASE_POINTS', 10)
```

### 4. Luôn handle errors
```python
try:
    result = some_operation()
except Exception as e:
    current_app.logger.error(f"Error: {e}", exc_info=True)
    return {"error": str(e)}, 500
```

### 5. Comment code phức tạp
```python
# [FIX] Legacy Mode Mapping - convert old mode names to new
if mode == 'review_due': mode = 'due_only'
```

### 6. Quản lý file tạm (Temporary Files)
- **Quy tắc**: Mọi file tạm (logs, debug scripts, test artifacts, archived code) **PHẢI** được đặt trong thư mục `temp/`.
- **Tuyệt đối không** để file rác (log, tmp script) ở root directory.
- Các file tests cũ/unused hoặc migrations cũ cần archive phải move vào `temp/tests_archive` hoặc `temp/migrations_archive`.

---

## 📊 CHANGELOG UPDATE TEMPLATE

Khi thêm entry vào `CHANGELOG.md`:

```markdown
## [Unreleased]

### 🚀 Added
- **Feature Name**: Mô tả ngắn gọn

### 🐛 Fixed
- Sửa lỗi XYZ trong `file.py`

### ♻️ Changed
- Refactor ABC để improve performance
```

---

## 🧪 TESTING REQUIREMENTS

### Khi nào PHẢI test?

| Change Type | Test Required |
|-------------|---------------|
| Logic in `logics/` | ✅ Bắt buộc |
| API endpoints | ✅ Bắt buộc |
| Services với business logic | ✅ Bắt buộc |
| Template HTML only | ❌ Optional |
| CSS changes | ❌ Optional |

### Test pattern
```python
def test_function_name_describes_behavior():
    # Arrange
    input_data = {...}
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected
```

---

## 🔍 TRƯỚC KHI BẮT ĐẦU TASK

1. **Đọc hiểu context**
   - Xem file liên quan
   - Hiểu architecture hiện tại
   
2. **Lên kế hoạch**
   - List các files cần thay đổi
   - Xác định impacts
   
3. **Hỏi rõ nếu không chắc**
   - Không đoán mò business logic
   - Xác nhận với user về edge cases

---

## 🎓 USER TAUGHT LESSONS (BÀI HỌC TỪ USER)

Ghi lại các bài học, quy tắc ưu tiên mà User đã trực tiếp hướng dẫn.

### 1. Backend Rendering First (BBCode/Markdown)
- **Context**: Khi hiển thị nội dung có định dạng (BBCode `[b]`, `[i]`, v.v.).
- **Lesson**: KHÔNG tự viết lại logic parse ở Frontend (JS). Phải kiểm tra và sử dụng các utility có sẵn ở Backend (như `mindstack_app.utils.content_renderer` hoặc `bbcode_parser.py`).
- **Why**: Tránh duplicated logic, đảm bảo nhất quán giữa các platform (Web/Mobile/API), và tận dụng code base có sẵn.
- **Action**: `import render_text_field` từ utils và xử lý data ngay trong API response.

---

## 📚 THAM KHẢO

- [coding_standards.md](../standards/coding_standards.md) - Chi tiết coding conventions
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture
- [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Common issues

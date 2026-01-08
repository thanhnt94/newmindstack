# MindStack Troubleshooting Guide

## Overview

Hướng dẫn xử lý các lỗi thường gặp khi phát triển và vận hành MindStack.

---

## 🔴 Critical Errors

### SyntaxError: Unexpected token '{'

**Triệu chứng:**
```
SyntaxError: Unexpected token '{'
TypeError: Cannot read properties of undefined (reading 'getFlashcardBatchUrl')
```

**Nguyên nhân:** Jinja2 syntax bị lỗi trong template (thừa space: `{ {` thay vì `{{`)

**Giải pháp:**
1. Tìm file template gây lỗi
2. Search `{ {` và replace bằng `{{`
3. Search `} }` và replace bằng `}}`

```jinja
{# ❌ Sai #}
{ { FlashcardConfig | tojson } }

{# ✅ Đúng #}
{{ FlashcardConfig | tojson }}
```

---

### UndefinedError: 'variable' is undefined

**Triệu chứng:**
```
jinja2.exceptions.UndefinedError: 'permissions' is undefined
```

**Nguyên nhân:** Biến không được truyền từ route vào template

**Giải pháp:**
```python
# routes.py
@bp.route('/stats/<int:item_id>')
def item_stats(item_id):
    return render_template('stats.html',
        stats=get_stats(item_id),
        permissions={'can_edit': True, 'edit_url': url_for('edit', id=item_id)}  # ← Thêm biến
    )
```

---

### NameError: name 'xxx' is not defined

**Triệu chứng:**
```
NameError: name 'datetime' is not defined
```

**Giải pháp:** Import module bị thiếu
```python
from datetime import datetime  # ← Thêm import
```

---

## 🟠 Database Errors

### Database is locked

**Triệu chứng:**
```
sqlite3.OperationalError: database is locked
```

**Nguyên nhân:** 
- Nhiều processes cùng truy cập SQLite
- Transaction chưa được commit/rollback

**Giải pháp:**

1. **Tăng timeout** trong `config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'connect_args': {
        'timeout': 30,  # Tăng từ mặc định 5
    },
}
```

2. **Đảm bảo commit/rollback:**
```python
try:
    db.session.add(new_item)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise e
```

3. **Dùng WAL mode** (thêm vào init):
```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
```

---

### No such table

**Triệu chứng:**
```
sqlite3.OperationalError: no such table: learning_progress
```

**Giải pháp:**
```python
# Trong Python shell
from mindstack_app import create_app
from mindstack_app.db_instance import db

app = create_app()
with app.app_context():
    db.create_all()
```

---

## 🟡 JavaScript Errors

### FlashcardConfig is undefined

**Triệu chứng:**
```
TypeError: Cannot read properties of undefined (reading 'getFlashcardBatchUrl')
```

**Nguyên nhân:** JavaScript chạy trước khi config được define

**Giải pháp:**
1. Đảm bảo config được define trong `<head>` hoặc trước scripts khác:
```html
<script>
    window.FlashcardConfig = {{ config | tojson | safe }};
</script>
<!-- Scripts khác sau đó -->
<script src="flashcard.js"></script>
```

2. Dùng DOMContentLoaded:
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const config = window.FlashcardConfig;
    // ...
});
```

---

### Variable redeclaration

**Triệu chứng:**
```
SyntaxError: Identifier 'xxx' has already been declared
```

**Giải pháp:**
```javascript
// ❌ Sai: khai báo lại biến
let config = {};
let config = {};

// ✅ Đúng: dùng const hoặc gán lại
const config = {};
// hoặc
config = {};
```

---

## 🟢 Template Errors

### Template not found

**Triệu chứng:**
```
jinja2.exceptions.TemplateNotFound: flashcard/index.html
```

**Giải pháp:**
1. Kiểm tra đường dẫn template:
```python
# routes.py
@bp.route('/flashcard')
def flashcard():
    # Đường dẫn từ templates/ folder
    return render_template('v3/pages/learning/flashcard/index.html')
```

2. Kiểm tra `template_folder` trong Blueprint:
```python
bp = Blueprint('flashcard', __name__, 
    template_folder='templates')  # ← Có đúng không?
```

---

### Include path issues

**Triệu chứng:** Include không tìm thấy file

**Giải pháp:** Dùng dynamic path:
```python
# routes.py
template_base_path = 'v3/pages/learning/flashcard'
return render_template(f'{template_base_path}/index.html',
    template_base_path=template_base_path)
```

```jinja
{# template #}
{% include template_base_path ~ '/_mobile.html' %}
```

---

## 🔵 API Errors

### 500 Internal Server Error

**Debug steps:**
1. Check server logs:
```bash
# Development
python start_mindstack_app.py

# Production
journalctl -u mindstack -f
```

2. Enable debug mode:
```python
app.run(debug=True)
```

3. Check route handler:
```python
@bp.route('/api/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        # ...
    except Exception as e:
        app.logger.error(f"Submit error: {e}")
        return jsonify({"error": str(e)}), 500
```

---

### CORS errors

**Triệu chứng:**
```
Access to fetch at 'xxx' from origin 'yyy' has been blocked by CORS policy
```

**Giải pháp:**
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

---

## 📱 Mobile Issues

### Layout not responsive

**Giải pháp:** Kiểm tra media queries:
```css
/* Mobile first */
.container {
    width: 100%;
    padding: 1rem;
}

/* Tablet */
@media (min-width: 768px) {
    .container {
        max-width: 720px;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    .container {
        max-width: 960px;
    }
}
```

---

### Touch events not working

**Giải pháp:**
```javascript
// Thêm touch event listeners
element.addEventListener('touchstart', handleTouch, {passive: true});
element.addEventListener('click', handleClick);
```

---

## 🛠️ Quick Debug Commands

```bash
# Check Python syntax
python -m py_compile mindstack_app/routes.py

# Run tests
python -m pytest tests/ -v

# Check imports
python -c "from mindstack_app import create_app; print('OK')"

# Database shell
python -c "
from mindstack_app import create_app
from mindstack_app.db_instance import db
app = create_app()
with app.app_context():
    # Your query here
    pass
"

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
# Windows
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

---

## 📚 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [API.md](API.md) - API reference

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

## 📁 TEMPLATE STRUCTURE

### Dashboard/Simple Pages → Single File
```
templates/v3/pages/module/dashboard/default/
└── index.html    # Responsive CSS với @media queries
```

### Session/Interactive → Separate Files
```
templates/v3/pages/module/session/default/
├── css/
├── js/
├── index.html
├── _mobile.html
├── _desktop.html
└── _card_*.html
```

### Quy tắc Template

1. **KHÔNG ĐẶT templates trong `modules/`** → Đặt trong `templates/v3/pages/`
2. **Mobile-first CSS** → Base styles cho mobile, `@media (min-width: ...)` cho desktop
3. **Dùng `template_base_path`** cho dynamic includes:
```jinja
{% include template_base_path ~ '/_mobile.html' %}
```

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

## 📚 THAM KHẢO

- [coding_standards.md](../standards/coding_standards.md) - Chi tiết coding conventions
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture
- [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Common issues

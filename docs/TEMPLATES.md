# 🎨 MindStack Template Guidelines

Tài liệu này quy định cấu trúc và các pattern bắt buộc khi phát triển giao diện (Frontend) trong MindStack.

---

## 1. Cấu trúc Thư mục (Directory Structure)

MindStack sử dụng 2 loại cấu trúc template tùy thuộc vào độ phức tạp của trang.

### Loại 1: Simple Pages (Dashboard, Landing)
Dùng cho các trang hiển thị thông tin, ít logic interactive phức tạp.

```
templates/v4/pages/[module]/[feature]/
└── index.html      # Chứa tất cả HTML + CSS/JS (nếu ít)
```

### Loại 2: Complex Components (Learning Session, Interactive Dashboard)
**BẮT BUỘC** dùng cho các trang có logic phức tạp, cần tách biệt code để dễ bảo trì.

```
templates/v4/pages/[module]/[feature]/[component]/
├── css/                  # Chứa file .css riêng của component
│   ├── desktop.css
│   └── mobile.css
├── js/                   # Chứa file .js logic
│   ├── logic.js
│   └── ui.js
├── index.html            # Entry point
├── _mobile.html          # Partial cho giao diện Mobile
└── _desktop.html         # Partial cho giao diện Desktop
```

> **QUAN TRỌNG**: Các assets (CSS/JS) của component phức tạp **PHẢI** đặt trong thư mục template tương ứng, **KHÔNG** đặt trong thư mục `static/` chung của app.

---

## 2. Component-Co-located Assets Pattern

Để giữ cho module độc lập (modular), các file CSS/JS đi kèm với template sẽ được serve trực tiếp từ thư mục template thông qua một route đặc biệt.

### Bước 1: Cấu trúc File
Đặt file vào subfolder `css/` hoặc `js/` trong đường dẫn template.

### Bước 2: Tạo Route Serve Asset (Python)
Trong file `routes.py` hoặc `dashboard.py` của module, thêm route sau:

```python
@blueprint.route('/assets/<path:filename>')
def serve_component_asset(filename):
    import os
    from flask import send_from_directory, current_app
    
    # Đường dẫn TUYỆT ĐỐI đến thư mục template của component
    # Ví dụ: templates/v4/pages/learning/vocabulary/dashboard
    directory = os.path.join(current_app.root_path, 'templates', 'v4', 'pages', '...', 'component_name')
    
    return send_from_directory(directory, filename)
```

### Bước 3: Sử dụng trong Jinja2
Link đến asset bằng `url_for` trỏ đến function route vừa tạo:

```html
<!-- CSS -->
<link rel="stylesheet" href="{{ url_for('module.serve_component_asset', filename='css/desktop.css') }}">

<!-- JS -->
<script src="{{ url_for('module.serve_component_asset', filename='js/logic.js') }}"></script>
```

---

## 3. Responsive Design Pattern

MindStack ưu tiên tách biệt code UI cho Mobile và Desktop khi giao diện quá khác biệt (thay vì cố gắng dùng CSS media queries cho mọi thứ).

### index.html (Main Layout)
Chịu trách nhiệm include đúng partial dựa trên CSS classes (thường dùng Tailwind `hidden` / `lg:block`).

```html
{% block content %}

    {# --- MOBILE VIEW --- #}
    <div class="lg:hidden">
        {% include 'path/to/_mobile.html' %}
    </div>

    {# --- DESKTOP VIEW --- #}
    <div class="hidden lg:block">
        {% include 'path/to/_desktop.html' %}
    </div>

{% endblock %}
```

### Naming Conventions
- Partial views luôn bắt đầu bằng dấu gạch dưới `_` (e.g., `_mobile.html`, `_sidebar.html`).
- File chính luôn là `index.html`.

---

## 4. Config & Data Passing

Để truyền dữ liệu từ Backend (Flask) sang Frontend (JS) một cách an toàn, tránh lỗi syntax formating.

### Pattern: Global Config Object
Trong `index.html`, khởi tạo object config trước khi load script chính.

```html
<script>
    // Define variables outside object to avoid Jinja/Formatter conflicts
    const _activeSetId = {{ active_set_id | default('null') }};
    const _capabilities = {{ container_capabilities | tojson | safe }};

    window.ComponentConfig = {
        activeSetId: _activeSetId,
        capabilities: _capabilities,
        apiUrls: {
            submit: "{{ url_for('module.submit') }}",
            stats: "{{ url_for('module.stats') }}"
        },
        csrfToken: "{{ csrf_token() }}"
    };
</script>

<script src="{{ url_for('module.serve_component_asset', filename='js/main.js') }}"></script>
```

### Pattern: API-First
Frontend nên hạn chế render logic phức tạp bằng Jinja2. Thay vào đó:
1. Render khung HTML cơ bản (skeleton).
2. Dùng JS fetch dữ liệu từ API (`/api/...`).
3. Render nội dung bằng JS (Client-side rendering).

Điều này giúp UI phản hồi nhanh hơn và tách biệt logic.

---

## 5. Checklist Kiểm Tra

Trước khi commit một features giao diện mới:

- [ ] File CSS/JS có nằm đúng trong thư mục template component không? (Nếu là Complex Component)
- [ ] Route `serve_asset` có hoạt động không? (Kiểm tra Log Network tab xem có 404 không)
- [ ] Responsive: Đã test trên cả Mobile view và Desktop view chưa?
- [ ] Console log: Có lỗi JS đỏ nào xuất hiện khi load trang không?
- [ ] Clean Code: Đã xóa các đoạn code CSS/JS inline cũ chưa?

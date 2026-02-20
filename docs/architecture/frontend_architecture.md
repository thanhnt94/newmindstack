# Kiến Trúc Giao Diện (Frontend Architecture & Themes)

MindStack được xây dựng theo mô hình **Server-Side Rendering (SSR)** bằng Flask + Jinja2, kết hợp với Vanilla JavaScript, HTML5 và CSS3. 

Điểm nổi bật của kiến trúc này là sự hỗ trợ Đa Giao Diện (Multi-Themes) ngay tại Server. Tùy thuộc vào thiết bị (Mobile hay Desktop) mà hệ thống sẽ trả về bộ khung (Layout) HTML rất khác nhau, tạo ra trải nghiệm Native mượt mà.

---

## 1. Cơ Chế Nhận Diện Thiết Bị (User-Agent Sniffing)

Khi có một Request từ phía Client (Ví dụ: `GET /dashboard`), hệ thống (thường qua tầng Middleware hoặc Base Controller) kiểm tra **User-Agent Header**:
- Nếu là **Mobile** (VD: Safari on iPhone, Chrome on Android): Cấu hình biến môi trường hoặc thuộc tính Request để định tuyến (Route) Engine Jinja tìm kiếm file Template trong thư mục `themes/aura_mobile/`.
- Nếu là **Desktop** (VD: Chrome on Mac/Windows): Định tuyến thư mục Template ưu tiên sang `themes/aura/`.
- Nếu vào trang **/admin**: Định tuyến ưu tiên thư mục Template sang `themes/admin/`.

Cơ chế này tránh kiểu "Responsive Web" cũ (load mọi DOM rối rắm rồi dùng CSS `@media` che đi). Nó giúp thiết bị tải đúng nguyên bản cấu trúc thẻ HTML cần thiết.

---

## 2. Cấu Trúc Thư Mục Giao Diện (`mindstack_app/themes/`)

Theme "Aura" là theme thiết kế mang phong cách hiện đại (Premium, Glassmorphism, Rounded UI).
Mỗi Theme (ví dụ `aura_mobile`) được cấu tạo bởi 2 thành phần: `static` và `templates`.

```text
mindstack_app/themes/aura_mobile/
├── static/                   # Resource (JS, CSS, Ảnh) phân bố theo Logical Module
│   ├── css/                  # Base styling
│   ├── js/                   # Base JS and utils
│   ├── img/
│   ├── vocab_flashcard/      # JS/CSS gắn riêng với Module Flashcard
│   └── gamification/
└── templates/
    └── aura_mobile/          # Các file HTML (*.html)
        ├── layouts/          # Layout cha (VD: base.html) - Chứa Header/Footer/Nav Bar
        ├── components/       # Các đoạn nhỏ (Macros) tái sử dụng (VD: button, user_card)
        ├── modules/          # Chứa các màn hình, sắp xếp tương ứng theo module Backend
        │   ├── auth/         # login.html, register.html
        │   ├── vocabulary/   # set_detail.html, mcq_session.html
        │   └── ops/          # Báo lỗi 500.html, 404.html
        └── index.html        # Trang chủ
```

---

## 3. Triết Lý Thiết Kế: Jinja2 Macros & Blocks

- **Tính Kế Thừa (Inheritance)**: Mọi View (ví dụ HTML của trang Flashcard Session) đều `{% extends 'aura_mobile/layouts/base.html' %}`. Việc này đảm bảo Thanh Điều Hướng Dưới (Bottom Nav Bar) hoặc Header luôn nhất quán. View con cung cấp nội dung thông qua `{% block content %}...{% endblock %}`.
- **Tính Tái Sử Dụng (Components/Macros)**: Các thẻ UI lặp lại nhiều lần (như Card Tiến Độ, Lời nhắc Streak, Nút Bấm Xinh xắn) được gói gọn trong thư mục `components/`. Khi cần Dùng, hệ thống gọi `{% from '.../components/button.html' import glass_button %}`, sau đó `{{ glass_button('Submit') }}`.
- Việc này giúp mã HTML vô cùng Clean, Clean tương đương như viết React.js hay Vue.js.

---

## 4. Tương Tác Vanilla JS (No Framework)

Để tối ưu tốc độ và không phụ thuộc, MindStack hạn chế dùng Framework Front-End lớn (React/Vue).
- Javascript được viết thủ công, thuần Vanilla (ES6+).
- Cấu hình Module Backend đưa dữ liệu (JSON/Dictionaries) cho Jinja render ra (VD: Gắn vào thẻ `<script id="session-data" type="application/json">...</script>`).
- Script JS đọc thẻ này lên bộ nhớ, tự thiết lập Listener, gán sự kiện cho các Button, và xử lý Audio, Animation (như lật Flipping Card, hoặc hiện Modal báo điểm).
- Cuối cùng gửi Data cho API bằng `fetch()` hoặc form Submit cổ điển.

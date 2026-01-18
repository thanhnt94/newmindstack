# BBCode Support Documentation

MindStack hỗ trợ BBCode để format nội dung trong nhiều hệ thống học tập.

---

## Tags được hỗ trợ

### Tags chuẩn (Built-in từ thư viện bbcode)

| Tag | Cú pháp | Kết quả | Ví dụ |
|-----|---------|---------|-------|
| **Bold** | `[b]text[/b]` | **text** | `[b]từ quan trọng[/b]` |
| **Italic** | `[i]text[/i]` | *text* | `[i]ví dụ[/i]` |
| **Underline** | `[u]text[/u]` | <u>text</u> | `[u]gạch dưới[/u]` |
| **Strikethrough** | `[s]text[/s]` | ~~text~~ | `[s]đã xóa[/s]` |
| **Color** | `[color=red]text[/color]` | <span style="color:red">text</span> | `[color=#ff0000]màu đỏ[/color]` |
| **Size** | `[size=20]text[/size]` | Chữ to hơn | `[size=14]chữ nhỏ[/size]` |
| **Quote** | `[quote]text[/quote]` | Khối trích dẫn | `[quote]Câu nói hay[/quote]` |
| **Code** | `[code]text[/code]` | `monospace` | `[code]const x = 1[/code]` |
| **URL** | `[url=link]text[/url]` | Hyperlink | `[url=https://google.com]Google[/url]` |
| **List** | `[list][*]item[/list]` | Danh sách | `[list][*]Mục 1[*]Mục 2[/list]` |

### Tags tùy chỉnh (MindStack Custom)

| Tag | Cú pháp | Mô tả |
|-----|---------|-------|
| **YouTube** | `[youtube]URL hoặc ID[/youtube]` | Nhúng video YouTube responsive |
| **Image** | `[img]URL[/img]` | Hiển thị hình ảnh với class `parsed-content-img` |

---

## Nơi BBCode được xử lý (Backend)

### Core Files

| File | Chức năng |
|------|-----------|
| [bbcode_parser.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/utils/bbcode_parser.py) | Parser chính, định nghĩa tags `[youtube]` và `[img]` |
| [content_renderer.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/utils/content_renderer.py) | Utility functions: `render_text_field()`, `render_content_dict()`, `strip_bbcode()` |

### Modules sử dụng BBCode rendering

| Module | File | Fields được render |
|--------|------|-------------------|
| **Flashcard Session** | [session_manager.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/flashcard/individual/session_manager.py) | `front`, `back`, `front_audio_content`, `back_audio_content`, `ai_explanation` |
| **Flashcard Engine** | [session_manager.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/flashcard/engine/session_manager.py) | `front`, `back`, `front_audio_content`, `back_audio_content`, `ai_explanation` |
| **Quiz Session** | [session_logic.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/quiz/individual/logics/session_logic.py) | `content` (toàn bộ dict), `ai_explanation`, `note_content` |
| **Vocab MCQ** | [logic.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/vocabulary/mcq/logic.py) | `question`, `choices`, `correct_answer` |
| **Vocab Typing** | [logic.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/vocabulary/typing/logic.py) | `prompt` |
| **Vocab Listening** | [logic.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/vocabulary/listening/logic.py) | `meaning` |
| **Vocab Stats** | [item_stats.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/sub_modules/vocabulary/stats/item_stats.py) | `front`, `back`, `meaning`, `example`, `example_meaning`, `ai_explanation` |
| **Learning Routes** | [routes.py](file:///c:/Code/MindStack/newmindstack/mindstack_app/modules/learning/routes.py) | `item_content` (trong log) |

---

## Templates hiển thị BBCode

Các template sau trực tiếp gọi `bbcode_to_html()` trong Jinja2:

| Template | Mô tả |
|----------|-------|
| [course_session.html](file:///c:/Code/MindStack/newmindstack/mindstack_app/templates/v4/pages/learning/course/course_session.html) | Nội dung bài học khóa học |
| [course_session.html (default)](file:///c:/Code/MindStack/newmindstack/mindstack_app/templates/v4/pages/learning/course/default/course_session.html) | Bản mặc định của bài học |
| [lessons.html](file:///c:/Code/MindStack/newmindstack/mindstack_app/templates/v4/pages/content_management/courses/lessons/lessons.html) | Quản lý bài học (preview) |

> [!NOTE]
> Các module khác (Flashcard, Quiz, MCQ, Typing, Listening, Stats) **không** gọi `bbcode_to_html()` trực tiếp trong template. Thay vào đó, BBCode được render **ở tầng backend (Python)** trước khi trả về JSON/HTML cho frontend.

---

## Fields KHÔNG được render BBCode

Các field sau sẽ giữ nguyên, không xử lý BBCode (được định nghĩa trong `content_renderer.py`):

- **IDs**: `item_id`, `container_id`, `group_id`, `user_id`
- **URLs**: `front_audio_url`, `back_audio_url`, `front_img`, `back_img`, `audio_url`
- **Metadata**: `correct_answer` (cho Quiz), `order_in_container`, `item_type`
- **Flags**: `supports_pronunciation`, `supports_writing`, `can_edit`

---

## Ví dụ sử dụng

### Flashcard

**Front:**
```
[b]Vocabulary[/b]: [i]Noun[/i]
```

**Back:**
```
[b]Từ vựng[/b]: [i]Danh từ[/i]

[youtube]https://youtube.com/watch?v=abc123[/youtube]
```

### Quiz Question

**Question:**
```
[b]Câu hỏi:[/b] Đâu là thủ đô của Việt Nam?

[color=blue]Gợi ý: Ở miền Bắc[/color]
```

**Explanation:**
```
Đáp án đúng là [b]Hà Nội[/b].

[youtube]dQw4w9WgXcQ[/youtube]
```

---

## Lưu ý kỹ thuật

1. **An toàn HTML**: BBCode được chuyển sang HTML an toàn, không cho phép inject script
2. **YouTube URL formats**: Hỗ trợ nhiều format:
   - `https://youtube.com/watch?v=VIDEO_ID`
   - `https://youtu.be/VIDEO_ID`
   - `https://youtube.com/embed/VIDEO_ID`
   - `https://youtube.com/shorts/VIDEO_ID`
   - Hoặc chỉ `VIDEO_ID` (11 ký tự)
3. **Nested tags**: Có thể lồng tags: `[b][i]bold italic[/i][/b]`
4. **Answer Validation**: Khi so sánh đáp án (Typing, Listening), BBCode được tự động loại bỏ bằng `strip_bbcode()`:
   - Đáp án lưu: `[b]hehe[/b]`
   - User nhập: `hehe`
   - Kết quả: ✅ Đúng
5. **Jinja2 Usage**: Khi dùng trong template, nhớ thêm `|safe`:
   ```jinja2
   {{ bbcode_to_html(content) | safe }}
   ```

### Lồng tags (Nesting)

Bạn có thể lồng các tags vào nhau. Tag bên trong sẽ ghi đè thuộc tính của tag bên ngoài nếu cùng loại.

**Ví dụ:**
```
[color=red]Sống một [color=blue][b]cuộc đời[/b][/color] hạnh phúc.[/color]
```

**Kết quả hiển thị:**
- "Sống một ": <span style="color:red">Màu đỏ</span>
- "cuộc đời": <span style="color:blue"><strong>Màu xanh dương + In đậm</strong></span> (Tag `color=blue` ghi đè `color=red` trong phạm vi của nó)
- " hạnh phúc.": <span style="color:red">Màu đỏ</span> (Trở lại màu của tag bao ngoài)

> [!WARNING]
> **Cú pháp tham số**:
> Vui lòng **KHÔNG** sử dụng dấu ngoặc kép `"` hoặc `'` bao quanh giá trị tham số.
> - ✅ Đúng: `[color=red]`, `[size=20]`
> - ❌ Sai: `[color="red"]`, `[size='20']` (Có thể gây lỗi CSS)
